"""하이브리드 RAG 검색 엔진 — 청킹 + BM25(어휘) + dense(의미) + RRF 융합.

프로토타입(prototypes/rag-search)의 검증된 하이브리드 로직을 백엔드로 이식한다.
- BM25: 외부 의존성(rank_bm25) 없이 Okapi 직접 구현(순수 numpy).
- dense: Gemini 임베딩(gemini-embedding-001) — 키 있으면 진짜 의미검색,
  없거나 429면 문자 n-gram 어휘 임베딩(numpy)으로 자동 폴백 → 항상 동작.
- 융합: RRF(Reciprocal Rank Fusion) — 점수 스케일이 달라도 안전하게 합친다.

인덱스는 코퍼스(문서 집합)가 바뀔 때만 다시 빌드하고, 청크 임베딩은 캐시한다.
"""

from __future__ import annotations

import math
import os
import re
import time

import numpy as np

_CHUNK_SIZE = 400
_CHUNK_OVERLAP = 60
_EMBED_MODEL = "gemini-embedding-001"
_LEX_DIM = 512  # 어휘 임베딩(폴백) 차원


# ── 토크나이즈 / 청킹 ────────────────────────────────────────────────
def _tokenize(text: str) -> list[str]:
    """BM25용 토크나이저. 한글은 단어 + 2-그램으로 보강해 재현율을 높인다."""
    words = re.findall(r"[0-9a-zA-Z]+|[가-힣]+", text.lower())
    tokens: list[str] = []
    for w in words:
        tokens.append(w)
        if len(w) >= 2 and re.match(r"[가-힣]+", w):
            tokens += [w[i : i + 2] for i in range(len(w) - 1)]
    return tokens


def _chunk(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """긴 문서를 겹침(overlap) 있는 청크로 자른다. 짧으면 통째로 1청크."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out, start = [], 0
    while start < len(text):
        out.append(text[start : start + size])
        start += size - overlap
    return out


# ── BM25 (Okapi, 직접 구현) ──────────────────────────────────────────
class _BM25:
    def __init__(self, corpus_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = corpus_tokens
        self.n = len(corpus_tokens)
        self.doc_len = np.array([len(d) for d in corpus_tokens], dtype="float32")
        self.avgdl = float(self.doc_len.mean()) if self.n else 0.0
        # 문서빈도 → idf
        df: dict[str, int] = {}
        self.tf: list[dict[str, int]] = []
        for doc in corpus_tokens:
            seen: dict[str, int] = {}
            for t in doc:
                seen[t] = seen.get(t, 0) + 1
            self.tf.append(seen)
            for t in seen:
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (self.n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def get_scores(self, query_tokens: list[str]) -> np.ndarray:
        scores = np.zeros(self.n, dtype="float32")
        if not self.n:
            return scores
        for i in range(self.n):
            tf, dl = self.tf[i], self.doc_len[i]
            s = 0.0
            for t in query_tokens:
                if t not in tf:
                    continue
                idf = self.idf.get(t, 0.0)
                freq = tf[t]
                denom = freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += idf * (freq * (self.k1 + 1)) / (denom or 1)
            scores[i] = s
        return scores


# ── 임베딩 (Gemini 우선, 어휘 폴백) ──────────────────────────────────
_EMBED_CACHE: dict[tuple[str, str], np.ndarray] = {}  # (embedder, text) → vec


def _gemini_key() -> str | None:
    from pathlib import Path

    env = Path(__file__).resolve().parent.parent / "prototypes" / "api-test" / ".env"
    try:
        for line in env.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            if k.strip() == "GEMINI_API_KEY":
                val = v.strip().strip('"').strip("'")
                if val:
                    return val
    except OSError:
        pass
    return os.getenv("GEMINI_API_KEY")


def _lexical_vec(text: str) -> np.ndarray:
    """문자 3-그램을 해싱한 TF 벡터(L2 정규화). 의미까지는 아니어도 형태 유사도 포착."""
    vec = np.zeros(_LEX_DIM, dtype="float32")
    s = re.sub(r"\s+", " ", (text or "").lower())
    grams = [s[i : i + 3] for i in range(max(0, len(s) - 2))] or [s]
    for g in grams:
        vec[hash(g) % _LEX_DIM] += 1.0
    norm = float(np.linalg.norm(vec))
    return vec / (norm + 1e-8)


def _embed_gemini(texts: list[str], task_type: str, key: str) -> np.ndarray | None:
    """Gemini 배치 임베딩 → 정규화 행렬. 실패(429 등)하면 None."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key, http_options={"timeout": 20000})
        vecs: list[list[float]] = []
        for i in range(0, len(texts), 20):  # 분당 한도 회피용 작은 배치
            batch = texts[i : i + 20]
            resp = client.models.embed_content(
                model=_EMBED_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            vecs.extend(e.values for e in resp.embeddings)
        arr = np.array(vecs, dtype="float32")
        arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-8
        return arr
    except Exception:
        return None


def _embed(texts: list[str], task_type: str, embedder: str, key: str | None) -> np.ndarray:
    """embedder('gemini'|'lexical')로 임베딩. 캐시 사용. gemini 실패 시 호출부가 폴백 결정."""
    out = np.zeros((len(texts), 0), dtype="float32")
    missing = [t for t in texts if (embedder, t) not in _EMBED_CACHE]
    if missing:
        if embedder == "gemini" and key:
            arr = _embed_gemini(missing, task_type, key)
            if arr is None:
                return out  # 신호: gemini 실패
            for t, v in zip(missing, arr, strict=False):
                _EMBED_CACHE[(embedder, t)] = v
        else:
            for t in missing:
                _EMBED_CACHE[(embedder, t)] = _lexical_vec(t)
    return np.array([_EMBED_CACHE[(embedder, t)] for t in texts], dtype="float32")


# ── 인덱스 (코퍼스 변경 시에만 재빌드) ───────────────────────────────
_INDEX: dict = {"sig": None}


def _signature(corpus: list[dict]) -> tuple:
    return tuple((d["source"], len(d.get("text") or "")) for d in corpus)


def _build_index(corpus: list[dict]) -> dict:
    chunks: list[dict] = []
    for d in corpus:
        for piece in _chunk(d.get("text") or ""):
            chunks.append({"source": d["source"], "text": piece})
    texts = [c["text"] for c in chunks]

    key = _gemini_key()
    embedder = "gemini" if key else "lexical"
    vectors = _embed(texts, "RETRIEVAL_DOCUMENT", embedder, key) if texts else None
    if embedder == "gemini" and (vectors is None or vectors.size == 0) and texts:
        embedder = "lexical"  # gemini 실패 → 어휘 폴백으로 전체 재임베딩
        vectors = _embed(texts, "RETRIEVAL_DOCUMENT", embedder, None)

    bm25 = _BM25([_tokenize(t) for t in texts]) if texts else None
    return {
        "sig": _signature(corpus),
        "chunks": chunks,
        "vectors": vectors,
        "bm25": bm25,
        "embedder": embedder,
    }


def _get_index(corpus: list[dict]) -> dict:
    if _INDEX.get("sig") != _signature(corpus):
        _INDEX.clear()
        _INDEX.update(_build_index(corpus))
    return _INDEX


# ── 하이브리드 검색 ──────────────────────────────────────────────────
def _coverage(query: str, text: str) -> int:
    """질의 토큰이 청크에 얼마나 등장하는지 0~100 (해석 가능한 신뢰도용)."""
    q = set(re.findall(r"[0-9a-zA-Z]+|[가-힣]+", query.lower()))
    if not q:
        return 0
    hay = text.lower()
    hits = sum(1 for w in q if w in hay or (len(w) > 2 and w[:-1] in hay))
    return min(100, round(100 * hits / len(q)))


def search(corpus: list[dict], query: str, k: int = 4) -> dict:
    """하이브리드 검색. 반환: {hits:[{source,text,score,dense,cover}], method, chunk_count, embedder}."""
    idx = _get_index(corpus)
    chunks = idx["chunks"]
    embedder = idx["embedder"]
    if not chunks:
        return {
            "hits": [],
            "found": False,
            "confidence": 0,
            "method": "빈 인덱스",
            "chunk_count": 0,
            "embedder": embedder,
        }

    # dense 검색(질의 임베딩). gemini 질의 임베딩 실패 시 dense 생략(BM25 단독).
    dense_scores = None
    key = _gemini_key() if embedder == "gemini" else None
    qv = _embed([query], "RETRIEVAL_QUERY", embedder, key)
    if qv.size and qv.shape[1] == idx["vectors"].shape[1]:
        dense_scores = idx["vectors"] @ qv[0]  # 코사인(정규화된 벡터의 내적)

    # BM25 검색.
    bm25_scores = idx["bm25"].get_scores(_tokenize(query))

    # RRF 융합.
    rrf: dict[int, float] = {}
    c = 60
    if dense_scores is not None:
        for rank, i in enumerate(np.argsort(-dense_scores)):
            rrf[int(i)] = rrf.get(int(i), 0.0) + 1 / (c + rank)
    for rank, i in enumerate(np.argsort(-bm25_scores)):
        rrf[int(i)] = rrf.get(int(i), 0.0) + 1 / (c + rank)

    # dense 코사인의 절대값은 무관 문장도 높게 나오므로(한국어 임베딩 특성),
    # '평균 대비 얼마나 튀는가(gap)'로 관련도를 판정한다.
    mean_dense = float(dense_scores.mean()) if dense_scores is not None else 0.0

    def _rel_dense(i: int) -> int:
        """평균 대비 상대 관련도 0~100 (gap 0.2 를 100으로)."""
        if dense_scores is None:
            return 0
        return round(100 * min(1.0, max(0.0, (float(dense_scores[i]) - mean_dense) / 0.2)))

    top = sorted(rrf, key=lambda i: -rrf[i])[:k]
    hits = []
    for i in top:
        text = chunks[i]["text"]
        cover = _coverage(query, text)
        score = max(cover, _rel_dense(i))  # 어휘 커버리지 vs 상대 의미관련도
        hits.append(
            {
                "source": chunks[i]["source"],
                "text": text,
                "score": score,
                "dense": round(float(dense_scores[i]), 3) if dense_scores is not None else 0.0,
                "cover": cover,
            }
        )

    # 근거 있음 판정: 어휘가 충분히 겹치거나(cover) 의미적으로 뚜렷이 튀면(gap).
    top_score = max((h["score"] for h in hits), default=0)
    found = top_score >= 34

    dense_label = (
        "Gemini dense" if (embedder == "gemini" and dense_scores is not None) else "어휘 dense"
    )
    return {
        "hits": hits,
        "found": found,
        "confidence": top_score if found else 0,
        "method": f"하이브리드 RAG (BM25+{dense_label}·RRF)",
        "chunk_count": len(chunks),
        "embedder": embedder,
    }


def chunk_counts(corpus: list[dict]) -> dict[str, int]:
    """문서(source)별 실제 청크 수 — rag_list_files 표기용."""
    idx = _get_index(corpus)
    counts: dict[str, int] = {}
    for ch in idx["chunks"]:
        counts[ch["source"]] = counts.get(ch["source"], 0) + 1
    return counts


# 마지막 검색이 걸린 시간(표시용) — search() 가 갱신.
def timed_search(corpus: list[dict], query: str, k: int = 4) -> tuple[dict, float]:
    t = time.time()
    res = search(corpus, query, k)
    return res, round(time.time() - t, 2)
