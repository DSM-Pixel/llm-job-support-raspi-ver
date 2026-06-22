"""서비스 계층 — 현재 전부 MOCK.

각 함수는 프론트엔드가 호출하는 "경계(boundary)"다. 입력·출력 계약(스키마)을
고정해 두었으므로, 백엔드 팀과 합칠 때는 함수 본문만 실제 구현으로 바꾸면
프론트엔드 수정 없이 동작한다.

교체 지점(이따 합치자):
    rag_search / rag_index → prototypes/rag-search/app.py
        (build_index, _hybrid_search, respond)
    labeling_detect        → prototypes/image-understanding/app.py
        (detect, analyze) + labeling.py(LabelRecord, to_coco/to_yolo)
    그 외(dashboard/report/datasets)는 별도 백엔드 연동 예정.

모든 응답에는 "backend": "MOCK" 을 실어 현재 가짜 데이터임을 명시한다.
"""

from __future__ import annotations

import os
import re

BACKEND = "MOCK"


# ────────────────────────────────────────────────────────────────────
# 1. 메인 대시보드 통계
# ────────────────────────────────────────────────────────────────────
def dashboard_stats() -> dict:
    """대시보드 상단 지표·주간 처리량·모델 상태·최근 활동. (MOCK)"""
    return {
        "backend": BACKEND,
        "stats": [
            {
                "icon": "▱",
                "delta": "↗ +124",
                "value": "2,748",
                "label": "색인 문서·소스",
                "sub": "청크 12,840",
            },
            {
                "icon": "◇",
                "delta": "↗ +3.9K",
                "value": "12,840",
                "label": "라벨 데이터셋",
                "sub": "검수 100%",
            },
            {
                "icon": "◎",
                "delta": "↗ +0.04",
                "value": "0.871",
                "label": "도로 파손 mAP@0.5",
                "sub": "YOLOe-L + SAM",
            },
            {
                "icon": "⌁",
                "delta": "↗ +18%",
                "value": "1,206",
                "label": "오늘 처리 작업",
                "sub": "질의·탐지·생성",
            },
        ],
        "weekly": [
            {"day": "월", "value": 42},
            {"day": "화", "value": 64},
            {"day": "수", "value": 48},
            {"day": "목", "value": 76},
            {"day": "금", "value": 58},
            {"day": "토", "value": 70},
            {"day": "일", "value": 52},
        ],
        "models": [
            {
                "name": "YOLOe-L 도로파손",
                "kind": "탐지",
                "load": 74,
                "state": "운영",
                "tone": "green",
            },
            {
                "name": "SAM 분할",
                "kind": "세그멘테이션",
                "load": 56,
                "state": "운영",
                "tone": "green",
            },
            {
                "name": "gemini-2.5-flash",
                "kind": "VLM·생성",
                "load": 40,
                "state": "운영",
                "tone": "green",
            },
            {
                "name": "도로파손 v3 파인튜닝",
                "kind": "학습",
                "load": 88,
                "state": "학습 중",
                "tone": "orange",
            },
        ],
        "activity": [
            {
                "icon": "⌗",
                "text": "pothole_set_2025Q2 라벨링 검수 완료",
                "meta": "김연우 · 12분 전",
            },
            {
                "icon": "⌕",
                "text": "공공데이터포털 ‘도로 파손 신고 현황’ 연계 동기화",
                "meta": "시스템 · 34분 전",
            },
            {"icon": "⇱", "text": "‘도로 파손 현황 분석 보고서’ 생성", "meta": "박서준 · 1시간 전"},
            {
                "icon": "▱",
                "text": "CCTV 이상행동 데이터셋 304건 업로드 완료",
                "meta": "이지은 · 3시간 전",
            },
        ],
    }


# ────────────────────────────────────────────────────────────────────
# 2. 자연어 질의 — 의도 라우팅 + 답변 (MOCK)
#    실제 연동: rag_search + labeling_detect 를 의도에 맞게 호출/오케스트레이션.
# ────────────────────────────────────────────────────────────────────
def route_query(question: str) -> dict:
    """질문 의도를 분류하고 답변 블록 + 후속 액션을 돌려준다. (MOCK)"""
    text = re.sub(r"\s+", " ", (question or "").strip())

    if re.search(r"포트홀|이미지|라벨|영역|박스", text):
        return {
            "backend": BACKEND,
            "intent": "image",
            "paragraphs": [
                "이미지 분석 작업으로 연결할 수 있습니다. 현재 요청은 <b>포트홀 위치 탐지와 라벨링</b>에 가장 적합합니다."
            ],
            "steps": [
                "도로 이미지에서 포트홀 후보 영역을 먼저 탐지합니다.",
                "심각도는 크기, 깊이 추정, 차량 손상 가능성 기준으로 분류합니다.",
                "결과는 COCO JSON 라벨 또는 보고서 문장으로 저장할 수 있습니다.",
            ],
            "actions": [
                {"label": "이미지 분석으로 이동", "href": "labeling.html", "primary": True},
                {"label": "데이터셋 보기", "href": "data.html", "primary": False},
            ],
        }

    if re.search(r"공공|데이터|통계|신고|현황|검색", text):
        return {
            "backend": BACKEND,
            "intent": "rag",
            "paragraphs": [
                "공공데이터 기반 질의로 판단됩니다. 도로 파손 신고 현황, 보수 예산, 점검 기준 문서를 함께 검색해 답변을 만들 수 있습니다.",
                "<b>요약:</b> 최근 도로 파손 신고는 증가 추세이며, 수도권 비중이 가장 높고 보수 예산 집행률은 지역별 편차가 있습니다.",
            ],
            "steps": [],
            "actions": [
                {"label": "RAG 검색으로 이동", "href": "rag.html", "primary": True},
                {"label": "보고서 생성", "href": "report.html", "primary": False},
            ],
        }

    if re.search(r"보고서|요약|리포트|문서", text):
        return {
            "backend": BACKEND,
            "intent": "report",
            "paragraphs": [
                "보고서 생성 요청으로 이해했습니다. 선택된 데이터 소스를 바탕으로 <b>요약, 통계 표, 출처</b>가 포함된 문서를 구성할 수 있습니다."
            ],
            "steps": [
                "보고서 유형을 현황 분석으로 설정합니다.",
                "기간은 최근 3년 기준이 적합합니다.",
                "공공데이터와 Vision AI 검수 결과를 출처로 포함합니다.",
            ],
            "actions": [{"label": "보고서 화면으로 이동", "href": "report.html", "primary": True}],
        }

    if re.search(r"대응|절차|추천|심각|긴급", text):
        return {
            "backend": BACKEND,
            "intent": "policy",
            "paragraphs": ["심각도 기반 대응 절차를 추천합니다."],
            "steps": [
                "<b>상:</b> 지름 30cm 이상 또는 깊이 5cm 이상이면 24시간 이내 긴급 보수 대상으로 분류합니다.",
                "<b>중:</b> 차량 손상 우려가 있으면 7일 이내 보수 계획에 포함합니다.",
                "<b>하:</b> 정기 점검 주기에 포함하고 재촬영 데이터를 누적합니다.",
            ],
            "actions": [{"label": "근거 문서 확인", "href": "rag.html", "primary": True}],
        }

    return {
        "backend": BACKEND,
        "intent": "general",
        "paragraphs": [
            "요청을 분석했습니다. 이 질문은 자연어 질의에서 처리한 뒤, 필요한 업무 화면으로 연결할 수 있습니다.",
            "더 정확한 답변을 위해 <b>분석 대상, 기간, 데이터 종류</b> 중 하나를 포함해서 질문하면 좋습니다.",
        ],
        "steps": [
            "예: 최근 3년 도로 파손 신고 현황을 요약해줘",
            "예: 이 이미지에서 포트홀 위치를 찾아줘",
            "예: 검색 결과를 보고서로 만들어줘",
        ],
        "actions": [],
    }


# ────────────────────────────────────────────────────────────────────
# 3. RAG 검색
#    검색(retrieval): 키워드 기반 질의-연관도(0~100) — 질문에 따라 근거가 달라진다.
#    답변(generation): GEMINI_API_KEY 가 있으면 실제 Gemini로 근거 기반 답변,
#                      없으면 질문/근거 기반 템플릿(MOCK)으로 폴백.
#    실제 고도화: prototypes/rag-search 의 임베딩+BM25 하이브리드로 retrieval 교체.
# ────────────────────────────────────────────────────────────────────

# 샘플 코퍼스(여러 주제) — 질문에 따라 다른 문서가 검색되도록 다양화.
_SAMPLE_DOCS = [
    {
        "source": "포트홀_보수_기준.md",
        "text": "심각(상) 등급은 발견 즉시 24시간 이내 긴급 보수, 보통(중)은 7일 이내, 경미(하)는 정기 보수 주기에 포함해 처리한다.",
    },
    {
        "source": "포트홀_보수_기준.md",
        "text": "심각(상) 포트홀 기준: 지름 30cm 이상 또는 깊이 5cm 이상이며 차량 손상 우려가 크다.",
    },
    {
        "source": "도로_균열_점검.md",
        "text": "균열 폭 3mm 이상이면 보수 대상으로 기록한다. 거북등 균열은 면적을 산정해 보수 물량을 추정한다.",
    },
    {
        "source": "도로_균열_점검.md",
        "text": "선형 균열은 표면 실링으로 우선 조치하고 진행 상황을 재촬영으로 추적한다.",
    },
    {
        "source": "시설물_점검_주기.md",
        "text": "가드레일·표지판 등 도로 시설물은 분기 1회 정기 점검하며 손상 발견 시 즉시 보수를 요청한다.",
    },
    {
        "source": "우천_긴급보수_지침.md",
        "text": "우천 시에는 상온 아스팔트 등 긴급 보수 공법으로 임시 복구한 뒤, 노면이 마르면 정식 보수한다.",
    },
    {
        "source": "도로보수_예산_현황.csv",
        "text": "도로보수 예산 집행률은 수도권 92%, 충청권 88%, 영남권 85%로 지역별 편차가 있다.",
    },
    {
        "source": "CCTV_이상행동_가이드.md",
        "text": "CCTV 영상에서 낙하물·무단횡단·차량 정지 같은 이상행동을 탐지해 관제에 알림을 보낸다.",
    },
]
# 사용자가 업로드했거나 웹에서 추가한 문서(모듈 메모리에 누적).
_user_docs: list[dict] = []

# 한국어 조사 근사 제거용(끝 한 글자).
_PARTICLES = ("은", "는", "이", "가", "을", "를", "의", "에", "도", "로", "와", "과", "만")


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", " ", (text or "").lower())


def _relevance(query: str, doc: dict) -> int:
    """질의-문서 연관도 0~100 (질의 토큰 커버리지 기반)."""
    q = set(_norm(query).split())
    if not q:
        return 0
    hay = _norm(doc["text"] + " " + doc["source"])
    hits = 0
    for w in q:
        stem = w[:-1] if len(w) > 2 and w[-1] in _PARTICLES else w
        if w in hay or stem in hay:
            hits += 1
    return min(100, round(100 * hits / len(q)))


def _gemini_key() -> str | None:
    """prototypes/api-test/.env 에서 GEMINI_API_KEY 를 한 번 로드."""
    if not _gemini_key.loaded:  # type: ignore[attr-defined]
        _gemini_key.loaded = True  # type: ignore[attr-defined]
        try:
            from pathlib import Path

            from dotenv import load_dotenv

            env = Path(__file__).resolve().parent.parent / "prototypes" / "api-test" / ".env"
            if env.exists():
                load_dotenv(env)
        except Exception:
            pass
        _gemini_key.value = os.getenv("GEMINI_API_KEY")  # type: ignore[attr-defined]
    return _gemini_key.value  # type: ignore[attr-defined]


_gemini_key.loaded = False  # type: ignore[attr-defined]
_gemini_key.value = None  # type: ignore[attr-defined]


def _generate_answer(query: str, hits: list[dict]) -> tuple[str, str]:
    """근거(hits) 기반 답변 생성. Gemini 우선, 실패/무키 시 템플릿. (answer, backend)"""
    context = "\n".join(f"- ({h['source']}) {h['text']}" for h in hits)
    key = _gemini_key()
    if key and hits:
        try:
            from google import genai

            client = genai.Client(api_key=key)
            prompt = (
                "너는 도로 유지보수 지식 도우미다. 아래 '근거'에 적힌 내용만으로 한국어로 "
                "2~3문장으로 간결히 답하라. 근거에 질문의 답이 없으면 추측하지 말고 "
                "반드시 '참고 문서에 해당 정보가 없습니다.' 라고만 답하라.\n\n"
                f"질문: {query}\n\n근거:\n{context}"
            )
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            text = (resp.text or "").strip()
            if text:
                return text, "GEMINI"
        except Exception:
            pass  # 한도/네트워크 오류 → 템플릿 폴백
    # 폴백: 질문 + 최상위 근거로 구성(질문에 따라 달라짐).
    if hits:
        top = hits[0]
        return (
            f"‘{query}’에 대해 색인 문서를 검색했습니다. 가장 관련 높은 근거(<b>{top['source']}</b>)에 따르면, "
            f"{top['text']}",
            "MOCK",
        )
    return (
        f"‘{query}’와(과) 관련된 근거 문서를 찾지 못했습니다. 문서를 색인하거나 질문을 더 구체화해 주세요.",
        "MOCK",
    )


# 이 연관도 미만이면 "관련 근거 없음"으로 처리(억지 유사 답변 방지).
_MIN_RELEVANCE = 40


def rag_search(query: str, top_k: int = 4) -> dict:
    """질의-연관도 기반 검색 + 근거 기반 답변(Gemini/폴백).

    연관도가 임계값(_MIN_RELEVANCE) 미만이면 비슷한 문서로 답을 만들어내지 않고
    '참고 문서에 관련 정보가 없다'고 명확히 응답한다.
    """
    q = (query or "").strip()
    corpus = _SAMPLE_DOCS + _user_docs
    scored = sorted(((_relevance(q, d), d) for d in corpus), key=lambda x: -x[0])
    relevant = [(s, d) for s, d in scored if s >= _MIN_RELEVANCE]

    # 관련 근거 없음 → 억지 답변 대신 명확히 "없음".
    if not relevant:
        best = scored[0][0] if scored else 0
        return {
            "backend": BACKEND,
            "query": q,
            "found": False,
            "answer": (
                f"참고 문서에서 ‘{q}’에 대한 관련 정보를 찾지 못했습니다. "
                "관련 문서를 색인에 추가하거나 질문을 바꿔 다시 시도해 주세요."
            ),
            "confidence": 0,
            "method": "근거 없음",
            "elapsed": "0.1s",
            "top_k": 0,
            "chunks": len(corpus),
            "matched": 0,
            "best": best,
            "sources": [],
        }

    chosen = relevant[:top_k]
    sources = [{"source": d["source"], "text": d["text"], "score": s} for s, d in chosen]
    answer, backend = _generate_answer(q, sources)
    confidence = round(sum(s["score"] for s in sources) / len(sources))
    return {
        "backend": backend,
        "query": q,
        "found": True,
        "answer": answer,
        "confidence": confidence,  # 0~100 (질의 연관도 평균)
        "method": "하이브리드 RAG · Gemini" if backend == "GEMINI" else "키워드 검색(MOCK)",
        "elapsed": "0.4s",
        "top_k": len(sources),
        "chunks": len(corpus),
        "matched": len(relevant),
        "sources": sources,
    }


def rag_index(
    docs: list[dict] | None = None,
    sources: list[str] | None = None,
    use_samples: bool = True,
) -> dict:
    """문서를 코퍼스에 색인한다. docs=[{name,text}] 형태(업로드/웹 추가 공용)."""
    added = 0
    for d in docs or []:
        name = (d.get("name") or "문서").strip()
        _user_docs.append({"source": name, "text": (d.get("text") or "").strip()})
        added += 1
    for name in sources or []:  # 이름만 온 경우(본문 없음)
        _user_docs.append({"source": str(name).strip(), "text": ""})
        added += 1

    corpus = (_SAMPLE_DOCS if use_samples else []) + _user_docs
    source_count = len({d["source"] for d in corpus})
    return {
        "backend": BACKEND,
        "indexed": True,
        "added": added,
        "source_count": source_count,
        "chunk_count": len(corpus),
        "message": f"색인됨 — 소스 {source_count}개 · 청크 {len(corpus)}개",
    }


# ────────────────────────────────────────────────────────────────────
# 4. 이미지 분석·라벨링 (MOCK)
#    실제 연동: prototypes/image-understanding detect()/analyze()
# ────────────────────────────────────────────────────────────────────
# box_2d 는 프로토타입과 동일한 Gemini 규약 [ymin, xmin, ymax, xmax] (0~1000 정규화).
_PRESET_FINDINGS = {
    "도로 파손/포트홀 찾기": [
        {
            "grade": "상",
            "tone": "red",
            "class_name": "포트홀",
            "note": "좌측 하단. 지름 약 35cm, 깊이 추정 6cm. 즉시 보수 대상.",
            "box_2d": [610, 80, 880, 360],
            "confidence": 94,
        },
        {
            "grade": "중",
            "tone": "orange",
            "class_name": "포트홀",
            "note": "중앙. 지름 약 18cm. 차량 손상 우려, 7일 이내 보수.",
            "box_2d": [520, 430, 660, 600],
            "confidence": 81,
        },
        {
            "grade": "중",
            "tone": "orange",
            "class_name": "선형 균열",
            "note": "우측 상단으로 진행. 표면 실링 권장.",
            "box_2d": [180, 640, 360, 920],
            "confidence": 73,
        },
    ],
    "이미지 전체 설명": [
        {
            "grade": "정보",
            "tone": "gray",
            "class_name": "장면",
            "note": "2차선 아스팔트 도로. 노면 일부 손상과 차선 마모가 관찰됩니다.",
            "box_2d": [40, 40, 960, 960],
            "confidence": 88,
        },
    ],
    "객체 목록 뽑기": [
        {
            "grade": "객체",
            "tone": "gray",
            "class_name": "차량",
            "note": "원거리 1대",
            "box_2d": [300, 420, 460, 560],
            "confidence": 90,
        },
        {
            "grade": "객체",
            "tone": "gray",
            "class_name": "차선",
            "note": "중앙 점선 1",
            "box_2d": [500, 470, 880, 530],
            "confidence": 86,
        },
        {
            "grade": "객체",
            "tone": "gray",
            "class_name": "포트홀",
            "note": "2개소",
            "box_2d": [640, 120, 820, 330],
            "confidence": 79,
        },
    ],
    "이상 상황 탐지": [
        {
            "grade": "주의",
            "tone": "orange",
            "class_name": "노면 침하",
            "note": "우측 하단 의심 영역. 추가 촬영 권장.",
            "box_2d": [620, 640, 900, 900],
            "confidence": 68,
        },
    ],
}


def labeling_detect(
    preset: str = "도로 파손/포트홀 찾기",
    custom_prompt: str = "",
    min_conf: int = 0,
    image_name: str = "",
) -> dict:
    """이미지 분석/탐지 결과(라벨 목록 + 신뢰도). (MOCK)

    실제 연동 시 detect(image, target, min_conf, engine) 의 반환을 이 스키마로 매핑.
    image_name 은 교체한 이미지 파일명(실제 연동 시 업로드 이미지 식별에 사용).
    """
    if custom_prompt.strip():
        findings = [
            {
                "grade": "분석",
                "tone": "gray",
                "class_name": "사용자 질문 응답",
                "note": f"‘{custom_prompt.strip()}’ 기준으로 이미지를 분석했습니다. (MOCK)",
            }
        ]
    else:
        findings = _PRESET_FINDINGS.get(preset, _PRESET_FINDINGS["도로 파손/포트홀 찾기"])

    return {
        "backend": BACKEND,
        "engine": "gemini-2.5-flash",
        "preset": preset,
        "image_name": image_name,
        "confidence": 0.91,
        "labels": findings,
    }


# 설명 분석(설명형) 프리셋별 프롬프트.
_ANALYZE_PROMPTS = {
    "도로 파손/포트홀 찾기": "이 도로 이미지에서 포트홀·균열 등 노면 파손을 찾아 위치와 심각도를 한국어로 항목별로 설명해줘.",
    "이미지 전체 설명": "이 이미지를 한국어로 전반적으로 설명해줘.",
    "객체 목록 뽑기": "이 이미지에 보이는 주요 객체들을 한국어로 목록으로 정리해줘.",
    "이상 상황 탐지": "이 이미지에서 위험하거나 이상한 상황이 있는지 한국어로 찾아 설명해줘.",
}


def analyze_image_vision(
    image_bytes: bytes,
    preset: str = "도로 파손/포트홀 찾기",
    custom_prompt: str = "",
    mime: str = "image/png",
) -> dict:
    """업로드 이미지를 실제 Gemini Vision으로 설명 분석. 키/오류 시 프리셋 MOCK 폴백."""
    prompt = custom_prompt.strip() or _ANALYZE_PROMPTS.get(
        preset, _ANALYZE_PROMPTS["이미지 전체 설명"]
    )
    key = _gemini_key()
    if key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            part = types.Part.from_bytes(data=image_bytes, mime_type=mime or "image/png")
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=[part, prompt])
            text = (resp.text or "").strip()
            if text:
                return {"backend": "GEMINI", "preset": preset, "description": text}
        except Exception:
            pass
    # 폴백: 프리셋 고정 결과를 설명 문장으로.
    findings = _PRESET_FINDINGS.get(preset, _PRESET_FINDINGS["도로 파손/포트홀 찾기"])
    desc = "\n".join(f"{f['class_name']}: {f['note']}" for f in findings)
    return {"backend": "MOCK", "preset": preset, "description": desc}


# ────────────────────────────────────────────────────────────────────
# 5. 보고서 생성 (MOCK)
# ────────────────────────────────────────────────────────────────────
def _report_table(period: str) -> dict:
    """현황 분석용 권역 통계 표."""
    return {
        "columns": ["권역", "신고 건수", "비중", "예산 집행률"],
        "rows": [
            ["수도권", "15,745", "41%", "92.1%"],
            ["충청권", "6,238", "16%", "88.4%"],
            ["영남권", "9,104", "24%", "85.0%"],
            ["호남권", "7,315", "19%", "83.7%"],
        ],
        "caption": f"권역별 도로 파손 신고·예산 ({period})",
    }


# 보고서 유형별 섹션 템플릿(유형에 따라 구성·내용이 달라진다).
def _report_sections(kind: str, period: str, sources: list[str]) -> list[dict]:
    src_line = ", ".join(sources) if sources else "선택된 소스 없음"
    if kind == "정책 브리핑":
        return [
            {
                "heading": "1. 배경",
                "body": f"{period} 도로 파손 신고가 지속 증가하여 보수 우선순위와 예산 배분에 대한 정책 판단이 필요하다. 본 브리핑은 {src_line} 를 근거로 한다.",
            },
            {
                "heading": "2. 핵심 이슈",
                "body": "심각(상) 등급 비중 상승, 지역별 예산 집행률 편차, 신고-보수 간 시차 확대가 핵심 이슈로 확인된다.",
            },
            {
                "heading": "3. 정책 제언",
                "body": "① 심각 등급 24시간 이내 긴급 보수 의무화 ② 집행률 저조 권역 예산 재배분 ③ Vision AI 자동 검수로 신고-보수 시차 단축.",
            },
            {
                "heading": "4. 기대 효과",
                "body": "사고 위험 감소, 예산 집행 효율화, 보수 대응 시간 단축이 기대된다.",
            },
        ]
    if kind == "검수 요약":
        return [
            {
                "heading": "1. 검수 개요",
                "body": f"{period} 수집·라벨링된 데이터셋을 대상으로 품질 검수를 수행하였다. 대상 소스: {src_line}.",
            },
            {
                "heading": "2. 데이터셋 품질",
                "body": "총 라벨 12,840건 중 검수 완료 100%. 클래스 분포는 포트홀 > 균열 > 도로파손 순이다.",
            },
            {
                "heading": "3. 라벨 정확도",
                "body": "샘플 검증 결과 박스 IoU 0.87, 클래스 정확도 96.2%. 경계 모호 케이스가 일부 확인된다.",
            },
            {
                "heading": "4. 보완 필요",
                "body": "야간·우천 이미지 보강, 경계 모호 라벨 재검수, 소수 클래스(맨홀 등) 추가 수집을 권고한다.",
            },
        ]
    # 기본: 현황 분석
    return [
        {
            "heading": "1. 개요",
            "body": f"{period} 전국 도로 파손(포트홀) 현황을 {src_line} 기준으로 분석하였다.",
        },
        {
            "heading": "2. 주요 현황",
            "body": "신고는 연평균 14.2% 증가, 2025년 누적 38,402건. 수도권 비중 41%로 가장 높다.",
        },
        {
            "heading": "3. 분석",
            "body": "Vision AI 검수 결과 심각(상) 등급 비율이 전 분기 대비 소폭 상승했고, 예산 집행률은 지역별 편차가 크다.",
        },
        {
            "heading": "4. 권고",
            "body": "심각 등급 24시간 이내 긴급 보수, 보통 등급 7일 이내 처리 기준 적용을 권고한다.",
        },
    ]


def generate_report(
    report_type: str = "현황 분석", period: str = "최근 3년", sources: list[str] | None = None
) -> dict:
    """선택한 유형·소스·기간에 맞춘 보고서 문서를 생성. (MOCK)"""
    kind = re.sub(r"[▥▤▢]", "", report_type).strip() or "현황 분석"
    srcs = [s for s in (sources or []) if s]
    return {
        "backend": BACKEND,
        "report_type": kind,
        "org": "GNSOFT",
        "date": "2026.6.22",
        "period": period,
        "title": f"도로 파손 {kind} 보고서",
        "subtitle": f"생성일 2026.6.22 · 소스 {len(srcs) or 3}개 · {period}",
        "sections": _report_sections(kind, period, srcs),
        "table": _report_table(period) if kind == "현황 분석" else None,
        "sources": srcs or ["도로 파손 신고 현황", "도로보수 예산 현황", "Vision AI 검수 리포트"],
    }


# ────────────────────────────────────────────────────────────────────
# 6. 데이터 관리 (MOCK)
# ────────────────────────────────────────────────────────────────────
def list_datasets() -> dict:
    """데이터셋 목록. (MOCK)"""
    return {
        "backend": BACKEND,
        "datasets": [
            {
                "name": "pothole_set_2025Q2",
                "kind": "라벨",
                "count": "4,210",
                "fmt": "COCO JSON",
                "state": "검수 완료",
                "tone": "green",
                "date": "2026. 6. 16.",
                "owner": "김연우",
            },
            {
                "name": "road_raw_2026Q1",
                "kind": "원본",
                "count": "18,402",
                "fmt": "JPG",
                "state": "정제 중",
                "tone": "orange",
                "date": "2026. 6. 14.",
                "owner": "이지은",
            },
            {
                "name": "도로 파손 신고 현황",
                "kind": "공공데이터",
                "count": "38,402",
                "fmt": "OpenAPI",
                "state": "연계됨",
                "tone": "blue",
                "date": "2026. 5. 28.",
                "owner": "시스템",
            },
            {
                "name": "포트홀_보수_기준.md",
                "kind": "문서",
                "count": "5 청크",
                "fmt": "Markdown",
                "state": "색인됨",
                "tone": "green",
                "date": "2026. 5. 20.",
                "owner": "박서준",
            },
            {
                "name": "cctv_anomaly_2026",
                "kind": "원본",
                "count": "304",
                "fmt": "MP4 프레임",
                "state": "검수 대기",
                "tone": "gray",
                "date": "2026. 6. 10.",
                "owner": "이지은",
            },
        ],
    }


def upload_dataset(name: str = "") -> dict:
    """업로드 대기열 추가. (MOCK)"""
    return {
        "backend": BACKEND,
        "queued": True,
        "message": f"업로드 대기열에 추가되었습니다{f' — {name}' if name else ''}.",
    }


# ────────────────────────────────────────────────────────────────────
# 7. RAG 보조 — 웹 검색 / 색인 초기화 (MOCK)
#    실제 연동: prototypes/rag-search web_search() / reset_index()
# ────────────────────────────────────────────────────────────────────
def rag_web_search(keyword: str) -> dict:
    """웹에서 후보 문서를 찾아온다. (MOCK)"""
    kw = (keyword or "").strip() or "도로 보수"
    results = [
        {
            "title": f"{kw} 관련 기술기준",
            "url": "https://www.law.go.kr",
            "snippet": "도로 유지·보수 일반 기준 및 등급별 처리 기한.",
        },
        {
            "title": f"{kw} 공공데이터",
            "url": "https://www.data.go.kr",
            "snippet": "도로 파손 신고·보수 현황 OpenAPI 데이터셋.",
        },
        {
            "title": f"{kw} 점검 매뉴얼",
            "url": "https://www.molit.go.kr",
            "snippet": "시설물 점검 주기 및 보수 공법 안내.",
        },
    ]
    return {
        "backend": BACKEND,
        "keyword": kw,
        "results": results,
        "message": f"‘{kw}’ 관련 웹 문서 {len(results)}건을 찾았습니다.",
    }


def rag_reset() -> dict:
    """색인 초기화 — 사용자가 추가한 문서를 비우고 샘플만 남긴다."""
    _user_docs.clear()
    source_count = len({d["source"] for d in _SAMPLE_DOCS})
    return {
        "backend": BACKEND,
        "indexed": True,
        "source_count": source_count,
        "chunk_count": len(_SAMPLE_DOCS),
        "message": f"색인을 초기화했습니다 — 샘플 소스 {source_count}개만 유지",
    }


# ────────────────────────────────────────────────────────────────────
# 8. 라벨 저장 (MOCK)
#    실제 연동: prototypes/image-understanding backend_client.save_labeling()
#    (해당 모듈도 이미 동일한 응답 계약을 따른다.)
# ────────────────────────────────────────────────────────────────────
def save_labeling(image_name: str = "", label_count: int = 0) -> dict:
    """라벨링 결과를 백엔드에 저장. (MOCK)"""
    if label_count <= 0:
        return {
            "status": "error",
            "backend": BACKEND,
            "record_id": "",
            "message": "저장할 라벨이 없습니다. 먼저 '분석하기'를 실행하세요.",
        }
    slug = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", image_name or "image").strip("_") or "image"
    return {
        "status": "ok",
        "backend": BACKEND,
        "record_id": f"20260622_{slug}",
        "message": f"[MOCK] 라벨 {label_count}건을 저장했습니다.",
    }
