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

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BACKEND = "MOCK"

# Gemini 호출용 스레드풀 — 429 재시도로 길게 행하는 호출을 하드 타임아웃으로 끊는다.
# (SDK의 http_options timeout/retry_options는 재시도 루프를 막지 못해 직접 끊는다.)
_GEMINI_POOL = ThreadPoolExecutor(max_workers=8)
_GEMINI_TIMEOUT_S = 15

# 이 서버 세션 동안의 실제 Gemini 사용량(대시보드 사용률 막대·상세용).
# retry_at: 429일 때 재시도 가능 추정 시각(epoch). 응답의 retryDelay 를 파싱.
# last_success_at: 마지막으로 호출이 '성공'한 시각(epoch). 서버 재시작에도 남도록 파일에 보존.
_gemini_usage = {
    "requests": 0,
    "success": 0,
    "tokens": 0,
    "rate_limited": False,
    "retry_at": 0.0,
    "last_success_at": 0.0,
}

# 분당(RPM)·일일(RPD) 사용률을 퍼센트로 보여주기 위한 호출 로그.
# 각 항목 {"ts": 요청시각, "tok": 사용토큰}. 24시간 지난 항목은 상태조회 때 정리.
_gemini_calls: list[dict] = []

# 마지막 성공 시각은 서버를 다시 켜도 유지되도록 작은 파일에 보존한다.
_GEMINI_STATE_FILE = os.path.join(os.path.dirname(__file__), ".gemini_state.json")


def _load_gemini_state() -> None:
    try:
        with open(_GEMINI_STATE_FILE, encoding="utf-8") as f:
            ts = float(json.load(f).get("last_success_at") or 0)
        if ts > 0:
            _gemini_usage["last_success_at"] = ts
    except Exception:
        pass


def _save_gemini_state() -> None:
    try:
        with open(_GEMINI_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_success_at": _gemini_usage["last_success_at"]}, f)
    except Exception:
        pass


_load_gemini_state()


def _gemini_generate(client, **kwargs):
    """client.models.generate_content 를 하드 타임아웃으로 감싼다.

    초과 시 TimeoutError 를 던져 호출부 except 가 MOCK 폴백을 타게 한다.
    요청 수·성공 수·사용 토큰·한도소진(429) 여부를 실제로 추적한다.
    """
    _gemini_usage["requests"] += 1
    call = {"ts": time.time(), "tok": 0}  # 분당/일일 사용률 집계용
    _gemini_calls.append(call)
    try:
        fut = _GEMINI_POOL.submit(lambda: client.models.generate_content(**kwargs))
        resp = fut.result(timeout=_GEMINI_TIMEOUT_S)
    except Exception as e:
        msg = str(e).lower()
        if any(k in msg for k in ("429", "resource_exhausted", "quota", "rate limit", "ratelimit")):
            _gemini_usage["rate_limited"] = True  # 한도 소진 관측
            # 응답에 retryDelay(예: "retryDelay":"30s")가 있으면 재시도 시각 추정.
            m = re.search(r"retrydelay['\"\s:]+(\d+(?:\.\d+)?)s", msg)
            delay = float(m.group(1)) if m else 60.0  # 없으면 분당 한도(60s) 가정
            _gemini_usage["retry_at"] = time.time() + delay
        raise
    _gemini_usage["rate_limited"] = False  # 성공했으니 가용
    _gemini_usage["retry_at"] = 0.0
    _gemini_usage["success"] += 1
    _gemini_usage["last_success_at"] = time.time()  # 마지막 성공 시각 기록(영속)
    _save_gemini_state()
    try:
        um = getattr(resp, "usage_metadata", None)
        total = getattr(um, "total_token_count", None) if um else None
        if total:
            _gemini_usage["tokens"] += int(total)
            call["tok"] = int(total)  # 분당 토큰 사용률 집계용
    except Exception:
        pass
    return resp


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
                "icon": "⬡",
                "delta": "↗ +3.9K",
                "value": "12,840",
                "label": "라벨 데이터셋",
                "sub": "검수 100%",
            },
            {
                "icon": "◉",
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
            {"day": "월", "count": 18},
            {"day": "화", "count": 27},
            {"day": "수", "count": 21},
            {"day": "목", "count": 32},
            {"day": "금", "count": 24},
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


# gemini-2.5-flash 무료 한도(참고용 기준).
_GEMINI_RPD = 250  # 일일 요청(Flash 250~1,000+)
_GEMINI_RPM = 15  # 분당 요청(5~15)
_GEMINI_TPM = 250_000  # 분당 토큰(입력 기준)
_GEMINI_CTX = 1_000_000  # 컨텍스트 윈도우


def real_model_status(yolo_ok: bool) -> list[dict]:
    """모델 상태 — YOLO(best.pt)·Gemini 는 실제 가용성/사용량, 나머지는 데모값."""
    u = _gemini_usage
    gemini_ok = bool(_gemini_key())
    if not gemini_ok:
        g_state, g_tone = "키 없음", "gray"
    elif u["requests"] == 0:
        g_state, g_tone = "대기", "gray"  # 아직 호출 없음 → 확인 전
    elif u["rate_limited"]:
        g_state, g_tone = "한도 소진", "orange"  # 429 관측됨
    else:
        g_state, g_tone = "운영", "green"
    # ── 한도별 사용률(%) 계산 ─────────────────────────────────────────
    # 분당(최근 60초) / 일일(최근 24시간) 실제 요청·토큰을 무료 한도 대비 비율로.
    now = time.time()
    _gemini_calls[:] = [c for c in _gemini_calls if now - c["ts"] < 86400]  # 24h 정리
    min_reqs = sum(1 for c in _gemini_calls if now - c["ts"] < 60)
    min_toks = sum(c["tok"] for c in _gemini_calls if now - c["ts"] < 60)
    day_reqs = len(_gemini_calls)  # = 최근 24시간 요청 수
    pct = lambda used, cap: min(100, round(used / cap * 100)) if cap else 0  # noqa: E731
    rpm_pct = pct(min_reqs, _GEMINI_RPM)
    tpm_pct = pct(min_toks, _GEMINI_TPM)
    rpd_pct = pct(day_reqs, _GEMINI_RPD)
    # 막대 = 한도에 가장 근접한 사용률(병목). 한도 소진이면 가득 채움.
    g_load = 100 if (gemini_ok and u["rate_limited"]) else max(rpm_pct, tpm_pct, rpd_pct)
    # 사용자 관점 — 지금 쓸 수 있는지 / 언제 다시 쓸 수 있는지에 집중.
    if not gemini_ok:
        status_v = "API 키 없음"
    elif u["requests"] == 0:
        status_v = "대기 — 아직 사용 전"
    elif u["rate_limited"]:
        status_v = "한도 소진 — 지금은 사용할 수 없어요"
    else:
        status_v = "사용 가능"
    g_detail = [{"k": "상태", "v": status_v}]
    # 마지막으로 호출이 성공한 시각(한도에 막히기 전 마지막 정상 응답).
    if gemini_ok:
        last_ok = u.get("last_success_at", 0)
        g_detail.append(
            {
                "k": "마지막 성공",
                "v": datetime.fromtimestamp(last_ok).strftime("%Y-%m-%d %H:%M")
                if last_ok
                else "성공 기록 없음",
            }
        )
    if gemini_ok:
        # 막대가 '남은 양'이 아니라 '사용량'임을 분명히 한다(이 서버 기준).
        g_detail.append(
            {"note": "아래는 한도 대비 ‘사용량’이에요 (이 서버가 보낸 요청 기준 · 남은 양 아님)."}
        )
        # 분당·일일 한도를 각각 퍼센트 막대로(수치 + 비율).
        g_detail.append(
            {"k": "분당 요청", "v": f"{min_reqs} / {_GEMINI_RPM}회  ({rpm_pct}%)", "pct": rpm_pct}
        )
        g_detail.append(
            {
                "k": "분당 토큰",
                "v": f"{min_toks:,} / {_GEMINI_TPM:,}  ({tpm_pct}%)",
                "pct": tpm_pct,
            }
        )
        g_detail.append(
            {"k": "하루 요청", "v": f"{day_reqs} / {_GEMINI_RPD}회  ({rpd_pct}%)", "pct": rpd_pct}
        )
    if gemini_ok and u["rate_limited"]:
        remain = int(max(0, u.get("retry_at", 0) - now))
        if remain <= 0:
            when = "지금 다시 시도하면 될 수 있어요"
        elif remain < 60:
            when = f"약 {remain}초 후"
        else:
            when = f"약 {remain // 60}분 {remain % 60}초 후"
        g_detail.append({"k": "다시 사용 가능", "v": when})
        g_detail.append(
            {
                "k": "한도 초기화",
                "v": "분당 한도는 약 1분 뒤 자동 복구 · 하루 한도는 자정(태평양 시간)에 초기화",
            }
        )
        # 사용량이 낮은데도 소진으로 뜨는 이유를 설명(서버 재시작/계정 단위 집계).
        g_detail.append(
            {
                "note": "위 사용량이 낮은데도 소진이면, 이 막대는 현재 서버가 보낸 양만 세기 때문이에요. "
                "구글 계정의 하루 한도는 서버를 다시 켜도 그대로라서, 측정값이 0이어도 소진으로 보일 수 있어요."
            }
        )
    return [
        {
            "name": "YOLOe-L 도로파손",
            "kind": "탐지",
            "load": 74 if yolo_ok else 0,
            "state": "운영" if yolo_ok else "모델 없음",
            "tone": "green" if yolo_ok else "gray",
        },
        {
            "name": "gemini-2.5-flash",
            "kind": f"VLM·생성 · 요청 {u['requests']}/{_GEMINI_RPD}",
            "load": g_load,
            "state": g_state,
            "tone": g_tone,
            "detail": g_detail,
        },
        {"name": "SAM 분할", "kind": "세그멘테이션", "load": 56, "state": "대기", "tone": "gray"},
        {
            "name": "도로파손 v3 파인튜닝",
            "kind": "학습",
            "load": 88,
            "state": "학습 중",
            "tone": "orange",
        },
    ]


# ────────────────────────────────────────────────────────────────────
# 2. 자연어 질의 — 의도 라우팅 + 답변 (MOCK)
#    실제 연동: rag_search + labeling_detect 를 의도에 맞게 호출/오케스트레이션.
# ────────────────────────────────────────────────────────────────────
# 날짜·시각이 들어간 질문 → 방대한 데이터에서 특정 기록을 찾아야 함(RAG).
_RE_DATETIME = re.compile(
    r"\d{4}\s*[.\-/년]\s*\d{1,2}|\d{1,2}\s*시|오전|오후|\bam\b|\bpm\b", re.IGNORECASE
)
# 이미지 1장을 직접 분석/라벨해야 하는 작업 → 이미지 분석·라벨링.
_RE_IMAGE = re.compile(r"영역|박스|바운딩|세그|라벨|이 ?이미지|이 ?사진|사진 ?분석|탐지해|검출해")
# 데이터셋을 조회해야 답할 수 있는 질문(수량·목록·위치 조회 등) → RAG.
_RE_DATA = re.compile(
    r"위치|어디|좌표|구간|지점|몇 ?건|건수|개수|목록|리스트|현황|통계|집계|검색|조회|찾아"
)
# 일반 지식·정의·방법·기능 소개 질문 → 그냥 답변.
# (이 시스템/RAG가 "뭐고 어떤 걸 해줄 수 있는지" 같은 메타 질문도 데이터 검색이 아니라 바로 답변)
_RE_GENERAL = re.compile(
    r"뭐야|뭐임|뭐고|뭔지|뭐냐|무엇|무슨|정의|개념|의미|소개|설명|"
    r"할 ?수 ?있|해 ?줄 ?수 ?있|어떤 ?(걸|것|거|기능|일|작업|도움)|기능|가능|"
    r"왜|어떻게|방법|차이|종류|원인|날씨|예방|효과"
)


def _classify_query(text: str) -> str:
    """자연어 질문 분류 → 'general'(바로 답변) / 'rag'(데이터 검색 연계) / 'image'(이미지 작업 연계)."""
    if _RE_DATETIME.search(text):  # 날짜·시각이 있으면 특정 기록 조회 → 데이터 검색
        return "rag"
    if _RE_IMAGE.search(text):  # 이미지 1장 분석/라벨 작업
        return "image"
    if _RE_DATA.search(text) and not _RE_GENERAL.search(text):  # 데이터셋 조회성 질문
        return "rag"
    return "general"  # 정의·방법·일반 지식 등은 바로 답변


def route_query(question: str) -> dict:
    """질문을 판단해 ① 일반 지식이면 바로 답하고, ② 방대한 데이터가 필요하면
    답하는 대신 적합한 화면(RAG 검색/이미지 분석)으로 연계 안내한다."""
    text = re.sub(r"\s+", " ", (question or "").strip())
    intent = _classify_query(text)

    if intent == "rag":
        from urllib.parse import quote

        return {
            "backend": "ROUTER",
            "intent": "rag",
            "answer": (
                "이 질문은 색인된 공공데이터에서 특정 기록을 직접 찾아야 정확히 답할 수 있습니다. "
                "데이터가 방대하므로 제가 바로 답하기보다 ‘RAG 공공데이터 검색’에서 찾는 것이 좋습니다. "
                "아래 버튼을 누르면 질문이 그대로 전달되어 색인된 데이터 안에서 검색합니다."
            ),
            "sources": [],
            "actions": [
                {
                    "label": "RAG 공공데이터 검색으로 이동",
                    "href": f"rag.html?q={quote(text)}",
                    "primary": True,
                },
            ],
        }

    if intent == "image":
        return {
            "backend": "ROUTER",
            "intent": "image",
            "answer": (
                "이 질문은 도로 이미지를 직접 분석해야 합니다. ‘이미지 분석·라벨링’ 화면에서 "
                "사진을 올리면 포트홀·균열 영역을 탐지·라벨링할 수 있습니다. 아래 버튼으로 이동하세요."
            ),
            "sources": [],
            "actions": [
                {"label": "이미지 분석·라벨링으로 이동", "href": "labeling.html", "primary": True},
            ],
        }

    # 일반 지식 질문 → 그냥 답변(웹 검색 그라운딩).
    answer, sources, backend = _web_answer(question)
    return {
        "backend": backend,
        "intent": "general",
        "answer": answer,
        "sources": sources,
        "actions": [],
    }


# ────────────────────────────────────────────────────────────────────
# 3. RAG 검색
#    검색(retrieval): 하이브리드 — BM25(어휘) + dense(Gemini 임베딩, 무키 시 어휘)
#                     를 RRF 로 융합. 구현은 backend/rag_engine.py.
#    답변(generation): GEMINI_API_KEY 가 있으면 실제 Gemini로 근거 기반 답변,
#                      없으면 질문/근거 기반 템플릿(MOCK)으로 폴백.
# ────────────────────────────────────────────────────────────────────

# 샘플 코퍼스(여러 주제) — 질문에 따라 다른 문서가 검색되도록 다양화.
_SAMPLE_DOCS = [
    {
        "source": "포트홀_보수_기준.md",
        "text": (
            "포트홀은 심각도에 따라 상·중·하 3등급으로 분류한다. 심각(상) 등급은 발견 즉시 24시간 이내 긴급 보수를 "
            "원칙으로 하며, 보통(중) 등급은 7일 이내, 경미(하) 등급은 정기 보수 주기에 포함해 처리한다. "
            "긴급 보수가 지연되면 차량 손상·사고로 이어질 수 있어 우선순위를 높게 둔다."
        ),
    },
    {
        "source": "포트홀_보수_기준.md",
        "text": (
            "심각(상) 포트홀의 판정 기준은 지름 30cm 이상 또는 깊이 5cm 이상이다. 이 경우 차량 타이어·휠 손상 "
            "우려가 크므로 즉시 안전조치(표지·콘 설치) 후 긴급 보수를 시행한다. 보수 공법은 상온/가열 아스팔트를 "
            "상황에 맞게 선택한다."
        ),
    },
    {
        "source": "도로_균열_점검.md",
        "text": (
            "균열은 폭 3mm 이상이면 보수 대상으로 기록한다. 거북등(망상) 균열은 면적을 산정해 보수 물량을 추정하고, "
            "표면 실링 또는 부분 재포장으로 대응한다. 균열 진행 속도가 빠른 구간은 하부 지지력 저하를 의심한다."
        ),
    },
    {
        "source": "도로_균열_점검.md",
        "text": (
            "선형(종·횡) 균열은 표면 실링으로 우선 조치하고 진행 상황을 재촬영해 추적한다. 균열이 포트홀로 "
            "발전하기 전에 조기 보수하는 것이 비용 효율적이다."
        ),
    },
    {
        "source": "시설물_점검_주기.md",
        "text": (
            "가드레일·표지판·중앙분리대 등 도로 시설물은 분기 1회 정기 점검을 원칙으로 한다. 손상·변형·부식이 "
            "발견되면 즉시 보수를 요청하고, 안전과 직결되는 가드레일은 우선순위를 높게 둔다. 점검 결과는 대장에 "
            "기록해 이력 관리한다."
        ),
    },
    {
        "source": "우천_긴급보수_지침.md",
        "text": (
            "우천 시에는 가열 아스팔트 시공이 어려우므로 상온 아스팔트(코일드믹스) 등 긴급 보수 공법으로 임시 "
            "복구한다. 노면이 마른 뒤 정식 보수로 전환하며, 임시 보수 구간은 재방문 점검 대상으로 등록한다."
        ),
    },
    {
        "source": "도로보수_예산_현황.csv",
        "text": (
            "최근 도로보수 예산 집행률은 수도권 92%, 충청권 88%, 영남권 85%, 호남권 84%로 지역별 편차가 있다. "
            "집행률이 낮은 권역은 신고 적체와 보수 지연이 누적되는 경향이 있어 예산 재배분 검토가 필요하다."
        ),
    },
    {
        "source": "CCTV_이상행동_가이드.md",
        "text": (
            "CCTV 영상에서 낙하물, 무단횡단, 차량 정지·역주행 같은 이상행동을 탐지해 관제센터에 자동 알림을 보낸다. "
            "야간·악천후에는 오탐이 늘 수 있어 신뢰도 임계값과 사람 확인 절차를 함께 둔다."
        ),
    },
    # 탐지로그 — 날짜·시각·위치가 든 기록. "2026.04.24 8시 포트홀 위치" 같은 질의가
    # 코퍼스 안에서만 검색되어 보고되도록 하는 샘플 데이터.
    {
        "source": "도로파손_탐지로그_2026Q2.csv",
        "text": (
            "2026-04-24 08:12 촬영 · 대전 유성구 문지로 272 부근에서 포트홀 1건 탐지(심각도 상, 지름 42cm). "
            "위치 위도 36.392 경도 127.391. 야간순찰 1조 등록, 24시간 내 긴급 보수 대상."
        ),
    },
    {
        "source": "도로파손_탐지로그_2026Q2.csv",
        "text": (
            "2026-04-24 14:30 촬영 · 대전 서구 둔산대로에서 포트홀 2건 탐지(심각도 중). "
            "위치 위도 36.351 경도 127.384. 7일 내 보수 예정."
        ),
    },
    {
        "source": "도로파손_탐지로그_2026Q2.csv",
        "text": (
            "2026-04-25 09:05 촬영 · 세종시 한누리대로에서 포트홀 1건 탐지(심각도 하). "
            "위치 위도 36.480 경도 127.289. 정기 보수 주기 포함."
        ),
    },
]
# 프로젝트(노트북)별 RAG 지식 — 문서·삭제분·샘플토글이 프로젝트마다 분리된다.
_user_docs_by_project: dict[str, list[dict]] = {}
_removed_by_project: dict[str, set[str]] = {}
_samples_on_by_project: dict[str, bool] = {}


def _pkey(project: str) -> str:
    return (project or "").strip() or "none"


def _udocs(project: str) -> list[dict]:
    return _user_docs_by_project.setdefault(_pkey(project), [])


def _removed(project: str) -> set[str]:
    return _removed_by_project.setdefault(_pkey(project), set())


def _samples_on(project: str) -> bool:
    return _samples_on_by_project.setdefault(_pkey(project), True)


def _active_corpus(project: str = "") -> list[dict]:
    """프로젝트의 활성 코퍼스(샘플 토글 + 사용자 문서, 삭제분 제외)."""
    base = (_SAMPLE_DOCS if _samples_on(project) else []) + _udocs(project)
    removed = _removed(project)
    return [d for d in base if d["source"] not in removed]


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
    """prototypes/api-test/.env 의 GEMINI_API_KEY 를 읽는다.

    .env 가 바뀌면(키 교체) 자동으로 다시 읽어 서버 재시작 없이 적용한다.
    키가 바뀌면 '한도 소진' 플래그도 초기화해 새 키가 바로 시도되게 한다.
    """
    from pathlib import Path

    env = Path(__file__).resolve().parent.parent / "prototypes" / "api-test" / ".env"
    try:
        mtime = env.stat().st_mtime
    except OSError:
        mtime = 0.0

    if mtime != _gemini_key.mtime:  # type: ignore[attr-defined]
        _gemini_key.mtime = mtime  # type: ignore[attr-defined]
        value = None
        try:
            for line in env.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                if k.strip() == "GEMINI_API_KEY":
                    value = v.strip().strip('"').strip("'") or None
                    break
        except OSError:
            pass
        if value is None:  # 파일에 없으면 환경변수 폴백
            value = os.getenv("GEMINI_API_KEY")
        # 키가 실제로 바뀌었으면 한도 소진 플래그 초기화(새 키에 새 기회).
        if value != _gemini_key.value:  # type: ignore[attr-defined]
            _gemini_usage["rate_limited"] = False
            _gemini_usage["retry_at"] = 0.0
        _gemini_key.value = value  # type: ignore[attr-defined]
    return _gemini_key.value  # type: ignore[attr-defined]


_gemini_key.mtime = None  # type: ignore[attr-defined]
_gemini_key.value = None  # type: ignore[attr-defined]


def _generate_answer(query: str, hits: list[dict]) -> tuple[str, str]:
    """근거(hits) 기반 답변 생성. Gemini 우선, 실패/무키 시 템플릿. (answer, backend)"""
    context = "\n".join(f"- ({h['source']}) {h['text']}" for h in hits)
    key = _gemini_key()
    if key and hits:
        try:
            from google import genai

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            prompt = (
                "너는 도로 유지보수 지식 도우미다. 아래 '근거'에 적힌 내용만으로 한국어로 "
                "2~3문장으로 간결히 답하라. 근거에 질문의 답이 없으면 추측하지 말고 "
                "반드시 '참고 문서에 해당 정보가 없습니다.' 라고만 답하라.\n\n"
                f"질문: {query}\n\n근거:\n{context}"
            )
            resp = _gemini_generate(client, model="gemini-2.5-flash", contents=prompt)
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


def rag_search(query: str, top_k: int = 4, project: str = "") -> dict:
    """질의-연관도 기반 검색 + 근거 기반 답변(Gemini/폴백).

    연관도가 임계값(_MIN_RELEVANCE) 미만이면 비슷한 문서로 답을 만들어내지 않고
    '참고 문서에 관련 정보가 없다'고 명확히 응답한다.
    """
    from . import rag_engine

    q = (query or "").strip()
    corpus = _active_corpus(project)
    result, elapsed = rag_engine.timed_search(corpus, q, top_k)
    hits = result["hits"]
    # 근거 있음 판정은 엔진(상대 gap/커버리지)에 맡기고, 표시 근거는 유효 점수만.
    relevant = [h for h in hits if h["score"] >= _MIN_RELEVANCE] or hits[:1]
    if not result["found"]:
        relevant = []

    # 관련 근거 없음 → 억지 답변 대신 명확히 "없음".
    if not relevant:
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
            "elapsed": f"{elapsed}s",
            "top_k": 0,
            "chunks": result["chunk_count"],
            "matched": 0,
            "best": hits[0]["score"] if hits else 0,
            "sources": [],
        }

    sources = [{"source": h["source"], "text": h["text"], "score": h["score"]} for h in relevant]
    answer, backend = _generate_answer(q, sources)
    confidence = round(sum(s["score"] for s in sources) / len(sources))
    # method 는 엔진이 알려주는 실제 검색 방식(BM25+dense·RRF) + 답변 생성 주체.
    answer_by = "Gemini" if backend == "GEMINI" else "템플릿"
    return {
        "backend": backend,
        "query": q,
        "found": True,
        "answer": answer,
        "confidence": confidence,  # 0~100 (질의 연관도 평균)
        "method": f"{result['method']} · {answer_by}",
        "elapsed": f"{elapsed}s",
        "top_k": len(sources),
        "chunks": result["chunk_count"],
        "matched": len(relevant),
        "sources": sources,
    }


def rag_index(
    docs: list[dict] | None = None,
    sources: list[str] | None = None,
    use_samples: bool = True,
    project: str = "",
) -> dict:
    """프로젝트 코퍼스에 문서를 색인한다. docs=[{name,text}] 형태(업로드/웹 추가 공용)."""
    udocs = _udocs(project)
    removed = _removed(project)
    added = 0
    for d in docs or []:
        name = (d.get("name") or "문서").strip()
        udocs.append({"source": name, "text": (d.get("text") or "").strip()})
        added += 1
    for name in sources or []:  # 이름만 온 경우(본문 없음)
        udocs.append({"source": str(name).strip(), "text": ""})
        added += 1
    # 다시 추가하면 삭제 상태 해제.
    for d in docs or []:
        removed.discard((d.get("name") or "문서").strip())
    # 색인 시 샘플 포함 여부 반영(토글 ON이면 전체 초기화로 빠졌던 샘플도 복원).
    _samples_on_by_project[_pkey(project)] = bool(use_samples)
    if use_samples:
        for d in _SAMPLE_DOCS:
            removed.discard(d["source"])

    corpus = _active_corpus(project)
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

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            part = types.Part.from_bytes(data=image_bytes, mime_type=mime or "image/png")
            resp = _gemini_generate(client, model="gemini-2.5-flash", contents=[part, prompt])
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
    report_type: str = "현황 분석",
    period: str = "최근 3년",
    sources: list[str] | None = None,
    include_chart: bool = True,
) -> dict:
    """선택한 유형·소스·기간에 맞춘 보고서 문서를 생성. (MOCK)"""
    kind = re.sub(r"[▥☰▢]", "", report_type).strip() or "현황 분석"
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
        "table": _report_table(period) if include_chart else None,
        "sources": srcs or ["도로 파손 신고 현황", "도로보수 예산 현황", "Vision AI 검수 리포트"],
    }


def _rich_report_sections(kind: str, period: str, focus: str) -> list[dict]:
    """웹 검색 불가 시 쓰는 풍부한 예시 섹션(초기 화면보다 상세, 불릿 포함)."""
    if kind == "정책 브리핑":
        return [
            {
                "heading": "1. 배경 및 목적",
                "body": (
                    f"{period} 도로 포트홀·파손 신고가 지속 증가하여 보수 우선순위와 예산 배분에 대한 정책 판단이 필요하다. "
                    f"본 브리핑은 {focus}을(를) 근거로 현행 대응 체계의 한계를 진단하고 개선 방향을 제시한다."
                ),
            },
            {
                "heading": "2. 현황 요약",
                "body": (
                    "- 전국 포트홀 신고는 연평균 약 14% 증가 추세\n"
                    "- 수도권 비중이 약 41%로 가장 높음\n"
                    "- 심각(상) 등급 비율이 전 분기 대비 소폭 상승"
                ),
            },
            {
                "heading": "3. 핵심 이슈",
                "body": (
                    "신고-보수 간 시차 확대, 지역별 예산 집행률 편차, 야간·우천 시 탐지 사각지대가 핵심 이슈로 확인된다. "
                    "특히 집행률이 낮은 권역에서 반복 신고가 누적되는 경향이 있다."
                ),
            },
            {
                "heading": "4. 정책 제언",
                "body": (
                    "- 심각 등급 24시간 이내 긴급 보수 의무화\n"
                    "- 집행률 저조 권역 예산 재배분 및 성과 연동\n"
                    "- Vision AI 자동 검수로 신고-보수 시차 단축"
                ),
            },
            {
                "heading": "5. 기대 효과",
                "body": (
                    "사고 위험 감소, 예산 집행 효율화, 보수 대응 시간 단축이 기대되며, 시민 신고 데이터와 AI 탐지의 연계로 "
                    "예방적 유지보수 전환이 가능하다."
                ),
            },
            {
                "heading": "6. 추진 일정(안)",
                "body": (
                    "- 1단계(1개월): 기준 정비 및 데이터 연계\n"
                    "- 2단계(3개월): 자동 검수 시범 적용\n"
                    "- 3단계(6개월): 전 권역 확대 및 성과 평가"
                ),
            },
        ]
    if kind == "검수 요약":
        return [
            {
                "heading": "1. 검수 개요",
                "body": (
                    f"{period} 수집·라벨링된 데이터셋을 대상으로 품질 검수를 수행하였다. 대상 소스: {focus}."
                ),
            },
            {
                "heading": "2. 데이터셋 규모",
                "body": (
                    "- 총 라벨 12,840건, 검수 완료 100%\n"
                    "- 클래스 분포: 포트홀 > 균열 > 도로파손\n"
                    "- 원본 이미지 18,706장, 공공데이터 37종"
                ),
            },
            {
                "heading": "3. 라벨 정확도",
                "body": (
                    "샘플 검증 결과 박스 IoU 0.87, 클래스 정확도 96.2%를 기록했다. 경계가 모호한 손상부에서 "
                    "오탐·미탐이 일부 확인된다."
                ),
            },
            {
                "heading": "4. 품질 이슈",
                "body": (
                    "- 야간·우천 이미지 표본 부족\n"
                    "- 소수 클래스(맨홀 등) 데이터 희소\n"
                    "- 경계 모호 라벨의 검수자 간 편차"
                ),
            },
            {
                "heading": "5. 보완 권고",
                "body": (
                    "야간·우천 이미지 보강, 경계 모호 라벨 재검수, 소수 클래스 추가 수집과 검수 가이드 보강을 권고한다."
                ),
            },
            {
                "heading": "6. 결론",
                "body": (
                    "전반적 품질은 양호하며, 위 보완을 반영하면 파인튜닝 학습 데이터로 활용 가능한 수준이다."
                ),
            },
        ]
    # 기본: 현황 분석
    return [
        {
            "heading": "1. 개요",
            "body": (
                f"{period} 전국 도로 파손(포트홀) 현황을 {focus} 기준으로 분석하였다. 신고·보수·예산·검수 결과를 종합해 "
                "현행 대응 수준과 개선 여지를 점검한다."
            ),
        },
        {
            "heading": "2. 핵심 수치",
            "body": (
                "- 2025년 누적 신고 38,402건(연평균 약 14% 증가)\n"
                "- 수도권 비중 41%로 최다\n"
                "- 평균 예산 집행률 약 87%"
            ),
        },
        {
            "heading": "3. 지역별 현황",
            "body": (
                "수도권은 신고량·집행률 모두 높은 반면, 일부 권역은 집행률이 낮아 보수 적체가 누적된다. "
                "아래 표의 권역별 수치를 참고한다."
            ),
        },
        {
            "heading": "4. 원인 분석",
            "body": (
                "- 노후 포장과 반복 하중\n"
                "- 동결-융해 및 우천 등 기상 요인\n"
                "- 신고-보수 시차로 인한 손상 확대"
            ),
        },
        {
            "heading": "5. Vision AI 검수 결과",
            "body": (
                "탐지 모델(YOLO) 기반 검수에서 심각(상) 등급 비율이 전 분기 대비 소폭 상승했다. 자동 탐지로 "
                "현장 확인 전 우선순위 분류가 가능하다."
            ),
        },
        {
            "heading": "6. 권고",
            "body": (
                "심각 등급 24시간 이내 긴급 보수, 보통 등급 7일 이내 처리 기준 적용과 집행률 저조 권역 예산 재배분을 권고한다."
            ),
        },
    ]


def _parse_md_sections(text: str) -> list[dict]:
    """'## 제목 / 본문' 마크다운을 섹션 목록으로 파싱. 본문의 줄바꿈·불릿(- )은 보존."""
    sections: list[dict] = []
    cur: dict | None = None
    for line in (text or "").splitlines():
        s = line.strip()
        if s.startswith("#"):
            if cur:
                sections.append(cur)
            cur = {"heading": s.lstrip("#").strip(), "body": ""}
        elif s and cur is not None:
            cur["body"] = (cur["body"] + "\n" + s) if cur["body"] else s
    if cur:
        sections.append(cur)
    return [x for x in sections if x["heading"] and x["body"]]


def revise_report(content: str, instruction: str) -> dict:
    """현재 보고서 본문을 사용자 지시대로 수정해 새 제목·섹션을 반환한다.

    - 수정 지시(예: '서론·본론·결론으로 나눠줘', '서론에 포트홀 정의 추가')면
      mode='edit' 로 수정된 전체 보고서(title/sections)를 돌려줘 프런트가 다시 렌더한다.
    - 단순 질문이면 mode='answer' 로 답변만 돌려준다.
    - Gemini 사용. 무키/한도/실패 시 안내 메시지(mode='answer').
    """
    body = (content or "").strip()
    instr = (instruction or "").strip()
    if not instr:
        return {"backend": "MOCK", "mode": "answer", "answer": "무엇을 도와드릴까요?"}

    key = _gemini_key()
    if key and body:
        try:
            from google import genai

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            prompt = (
                "너는 한국어 보고서 편집 도우미다. 아래 '현재 보고서'를 사용자 '지시'대로 처리하라.\n"
                "- 보고서를 고치는 지시면: 수정된 전체 보고서를 다음 형식으로만 출력한다.\n"
                "  · 첫 줄: '# 제목'\n"
                "  · 이후 각 섹션: '## 소제목' 한 줄 + 다음 줄부터 본문(2~4문장 또는 '- ' 불릿)\n"
                "  · 머리말/맺음말/코드펜스(```) 없이 본문만.\n"
                "- 보고서를 고치지 않는 단순 질문이면: 'ANSWER:' 로 시작해 2~4문장으로 답한다.\n\n"
                f"지시: {instr}\n\n현재 보고서:\n{body[:6000]}"
            )
            resp = _gemini_generate(client, model="gemini-2.5-flash", contents=prompt)
            text = (resp.text or "").strip().strip("`")
            if text.upper().startswith("ANSWER:"):
                return {
                    "backend": "GEMINI",
                    "mode": "answer",
                    "answer": text.split(":", 1)[1].strip(),
                }
            # 첫 '# 제목' 줄을 분리하고 나머지를 섹션으로 파싱.
            title = ""
            lines = text.splitlines()
            if lines and lines[0].lstrip().startswith("# "):
                title = lines[0].lstrip().lstrip("#").strip()
                text = "\n".join(lines[1:])
            sections = _parse_md_sections(text)
            if sections:
                return {"backend": "GEMINI", "mode": "edit", "title": title, "sections": sections}
            if text.strip():
                return {"backend": "GEMINI", "mode": "answer", "answer": text.strip()}
        except Exception:
            pass

    return {
        "backend": "MOCK",
        "mode": "answer",
        "answer": (
            "AI 사용량(토큰)이 일시적으로 소진되어 지금은 보고서 수정을 적용하지 못했습니다. "
            "사용량이 회복되거나 API 키를 교체하면 ‘서론·본론·결론으로 나눠줘’, "
            "‘서론에 포트홀이 무엇인지 추가해줘’ 같은 지시로 실제 수정됩니다. "
            "그 사이에도 보고서 본문을 직접 클릭해 수정할 수 있습니다."
        ),
    }


def _grounding_sources(resp) -> list[dict]:
    """Gemini 응답의 grounding 메타에서 실제 출처(제목+URL)를 추출."""
    out: list[dict] = []
    try:
        gm = resp.candidates[0].grounding_metadata
        for ch in getattr(gm, "grounding_chunks", None) or []:
            w = getattr(ch, "web", None)
            if w and getattr(w, "uri", None):
                out.append({"title": w.title or w.uri, "url": w.uri})
    except Exception:
        pass
    seen, ded = set(), []
    for s in out:
        if s["title"] in seen:
            continue
        seen.add(s["title"])
        ded.append(s)
    return ded[:6]


def _web_answer(question: str) -> tuple[str, list[dict], str]:
    """질문에 웹 검색(Gemini 그라운딩)으로 답한다. (answer, sources, backend)"""
    q = (question or "").strip()
    if not q:
        return ("무엇이 궁금한지 입력해 주세요.", [], "MOCK")
    key = _gemini_key()
    if key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            tool = types.Tool(google_search=types.GoogleSearch())
            prompt = (
                "너는 도로 유지보수·공공데이터 업무 도우미다. 다음 질문에 한국어로 정확하고 친절하게 "
                "답하라. 필요하면 웹을 검색해 최신 사실·수치에 근거하라. 3~6문장으로 답하고, 핵심은 "
                f"'- ' 불릿으로 정리해도 좋다.\n\n질문: {q}"
            )
            resp = _gemini_generate(
                client,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(tools=[tool]),
            )
            text = (resp.text or "").strip()
            if text:
                return (text, _grounding_sources(resp), "GEMINI_WEB")
        except Exception:
            pass
    return (
        "AI 사용량(토큰)이 일시적으로 소진되어 지금은 답변을 생성하지 못했습니다. "
        "사용량이 회복되거나 API 키를 교체하면 자동으로 실제 답변이 표시됩니다. "
        "그 사이에는 아래 버튼으로 관련 작업 화면에서 직접 처리할 수 있습니다.",
        [],
        "MOCK",
    )


def ask_about_text(context: str, question: str) -> dict:
    """이 페이지의 글/문서 내용만 근거로 질의응답(보고서 등). Gemini, 실패 시 안내."""
    q = (question or "").strip()
    ctx = (context or "").strip()
    if not q:
        return {"backend": "MOCK", "answer": "질문을 입력해 주세요."}
    if not ctx:
        return {
            "backend": "MOCK",
            "answer": "이 페이지에 참조할 내용이 아직 없습니다. 먼저 보고서를 생성해 주세요.",
        }
    key = _gemini_key()
    if key:
        try:
            from google import genai

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            prompt = (
                "아래 '문서'의 내용만 근거로 질문에 한국어로 간결히(2~4문장) 답하라. "
                "문서에 답이 없으면 '이 문서에는 해당 내용이 없습니다.'라고만 답하라.\n\n"
                f"문서:\n{ctx[:6000]}\n\n질문: {q}"
            )
            resp = _gemini_generate(client, model="gemini-2.5-flash", contents=prompt)
            text = (resp.text or "").strip()
            if text:
                return {"backend": "GEMINI", "answer": text}
        except Exception:
            pass
    return {
        "backend": "MOCK",
        "answer": "AI 사용량(토큰)이 일시적으로 소진되었습니다. 회복되거나 API 키 교체 시 자동으로 답변이 표시됩니다.",
    }


def ask_about_image(image_bytes: bytes, question: str, mime: str = "image/png") -> dict:
    """이 페이지에 올린 이미지만 근거로 질의응답(라벨링 등). Gemini Vision."""
    q = (question or "").strip()
    if not q:
        return {"backend": "MOCK", "answer": "질문을 입력해 주세요."}
    key = _gemini_key()
    if key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            part = types.Part.from_bytes(data=image_bytes, mime_type=mime or "image/png")
            prompt = f"이 이미지만 보고 질문에 한국어로 간결히(2~4문장) 답하라.\n질문: {q}"
            resp = _gemini_generate(client, model="gemini-2.5-flash", contents=[part, prompt])
            text = (resp.text or "").strip()
            if text:
                return {"backend": "GEMINI", "answer": text}
        except Exception:
            pass
    return {
        "backend": "MOCK",
        "answer": "AI 사용량(토큰)이 일시적으로 소진되었습니다. 회복되거나 API 키 교체 시 자동으로 이미지 답변이 표시됩니다.",
    }


def generate_report_web(
    report_type: str = "현황 분석",
    period: str = "최근 3년",
    sources: list[str] | None = None,
    query: str = "",
    include_chart: bool = True,
) -> dict:
    """Gemini Google 검색 그라운딩으로 실제 웹 데이터 기반 보고서 생성. 실패 시 MOCK 폴백.

    검색 주제는 보고서 유형 + 선택한 데이터 소스에서 구성한다(별도 입력 불필요).
    """
    kind = re.sub(r"[▥☰▢]", "", report_type).strip() or "현황 분석"
    srcs = [re.sub(r"[▱◫⬡☰▢]", "", s).strip() for s in (sources or []) if s]
    srcs = [s for s in srcs if s]
    focus = ", ".join(srcs) if srcs else "신고 현황, 보수 예산, 검수 결과"
    topic = (query or "").strip() or f"한국 도로 포트홀·파손 {kind} ({focus})"
    key = _gemini_key()
    if key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            tool = types.Tool(google_search=types.GoogleSearch())
            prompt = (
                f"'{topic}' 주제로 한국어 {kind} 보고서를 풍부하고 충실하게 작성해라. "
                "반드시 웹을 검색해 최신 사실·수치에 근거하라. 모든 섹션에 구체적 수치·연도·지역·"
                f"기관명 등 근거를 포함하라. 기간 관점: {period}.\n"
                "출력 형식:\n"
                "- 6~7개 섹션. 각 섹션은 '## N. 제목' 한 줄, 다음 줄부터 본문.\n"
                "- 본문은 3~5문장으로 충분히 서술하되, 핵심 항목은 '- '로 시작하는 불릿 3개 내외로 정리.\n"
                "- 가능하면 '핵심 수치', '지역별/연도별 현황', '원인 분석', '대응 방안/권고' 섹션을 포함.\n"
                "- 머리말/맺음말/코드펜스 없이 섹션만 출력."
            )
            resp = _gemini_generate(
                client,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(tools=[tool]),
            )
            sections = _parse_md_sections(resp.text or "")
            sources = _grounding_sources(resp)
            if sections:
                return {
                    "backend": "GEMINI_WEB",
                    "report_type": kind,
                    "org": "GNSOFT",
                    "date": "2026.6.23",
                    "period": period,
                    "query": topic,
                    "title": f"도로 파손 {kind} 보고서",
                    "subtitle": f"생성일 2026.6.23 · 웹 검색 기반 · {period} · 소스 {len(srcs) or 3}개",
                    "sections": sections,
                    "table": _report_table(period) if include_chart else None,
                    "sources": sources
                    or [{"title": "Google 검색", "url": "https://www.google.com"}],
                }
        except Exception:
            pass
    # 폴백: 웹 검색 불가 시에도 초기 화면보다 풍부한 보고서로(내용이 바뀌도록).
    return {
        "backend": "MOCK",
        "report_type": kind,
        "org": "GNSOFT",
        "date": "2026.6.23",
        "period": period,
        "title": f"도로 파손 {kind} 보고서",
        "subtitle": f"생성일 2026.6.23 · 예시(웹 검색 불가) · {period} · 소스 {len(srcs) or 3}개",
        "sections": _rich_report_sections(kind, period, focus),
        "table": _report_table(period) if include_chart else None,
        "sources": srcs or ["도로 파손 신고 현황", "도로보수 예산 현황", "Vision AI 검수 리포트"],
    }


def generate_report_from_rag(
    question: str,
    answer: str,
    sources: list[dict] | None = None,
    report_type: str = "현황 분석",
    period: str = "최근 3년",
    include_chart: bool = True,
) -> dict:
    """RAG 검색 결과(질문·AI답변·근거 문서)를 그대로 이어받아 보고서로 확장."""
    kind = re.sub(r"[▥☰▢]", "", report_type).strip() or "현황 분석"
    srcs = sources or []
    file_names: list[str] = []
    for s in srcs:
        name = (s.get("source") or "").strip()
        if name and name not in file_names:
            file_names.append(name)

    evidence = "\n".join(f"- ({s.get('source', '')}) {s.get('text', '')}" for s in srcs)
    context = f"질문: {question}\n\nAI 답변:\n{answer}\n\n근거 문서:\n{evidence}"

    key = _gemini_key()
    if key and (answer or srcs):
        try:
            from google import genai

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            prompt = (
                f"아래 'RAG 검색 결과'(질문·AI 답변·근거 문서)를 바탕으로 한국어 {kind} 보고서를 "
                "충실하게 작성하라. 근거 문서에 있는 내용만 사용하고(추측 금지), 질문과 답변을 보고서 "
                "형태로 확장하라.\n"
                "출력: 5~6개 섹션. 각 섹션 '## N. 제목' 한 줄, 다음 줄에 본문 2~4문장 또는 '- ' 불릿. "
                "머리말/맺음말/코드펜스 없이 섹션만.\n\n" + context
            )
            resp = _gemini_generate(client, model="gemini-2.5-flash", contents=prompt)
            sections = _parse_md_sections(resp.text or "")
            if sections:
                return {
                    "backend": "GEMINI_RAG",
                    "report_type": kind,
                    "org": "GNSOFT · RAG 검색 보고서",
                    "date": "2026.6.24",
                    "period": period,
                    "query": question,
                    "title": question.strip() or f"{kind} 보고서",
                    "subtitle": f"생성일 2026.6.24 · RAG 검색 결과 기반 · 근거 {len(file_names)}건",
                    "sections": sections,
                    "table": None,
                    "sources": file_names or ["RAG 근거 문서"],
                }
        except Exception:
            pass

    # 폴백: RAG 내용을 그대로 섹션으로 구성(질문/답변/근거).
    sections = [
        {"heading": "1. 질문", "body": question or "—"},
        {"heading": "2. AI 답변 요약", "body": answer or "—"},
    ]
    if evidence:
        sections.append({"heading": "3. 근거 문서", "body": evidence})
    sections.append(
        {
            "heading": f"{len(sections) + 1}. 종합 의견",
            "body": "위 질문과 근거 문서를 바탕으로 추가 분석·보수 우선순위 검토가 필요하다.",
        }
    )
    return {
        "backend": "MOCK",
        "report_type": kind,
        "org": "GNSOFT · RAG 검색 보고서",
        "date": "2026.6.24",
        "period": period,
        "query": question,
        "title": question.strip() or f"{kind} 보고서",
        "subtitle": f"생성일 2026.6.24 · RAG 검색 결과 기반(예시) · 근거 {len(file_names)}건",
        "sections": sections,
        "table": None,
        "sources": file_names or ["RAG 근거 문서"],
    }


def generate_report_activity(
    activities: list[dict] | None = None,
    start: str = "",
    end: str = "",
    report_type: str = "활동 요약",
    include_chart: bool = True,
) -> dict:
    """사용자가 웹에서 한 활동(검색·이미지 분석·라벨·문서 등)을 분석·통계 낸 보고서."""
    acts = activities or []
    n = len(acts)
    period_label = f"{start} ~ {end}" if (start or end) else "전체 기간"

    from datetime import datetime

    # 버튼 텍스트의 아이콘(☰ 활동 통계, ▢ 상세 내역 등)을 떼고 유형만 추출.
    rtype = re.sub(r"[▥☰▢◫]", "", report_type or "활동 요약").strip() or "활동 요약"
    page_ko = {
        "query": "자연어 질의",
        "rag": "RAG 검색",
        "labeling": "이미지 분석·라벨링",
        "report": "요약·보고서",
        "data": "데이터 관리",
        "dashboard": "대시보드",
    }

    def _ts(ts, fmt):
        try:
            return datetime.fromtimestamp(float(ts) / 1000).strftime(fmt)
        except Exception:
            return "-"

    by_type: dict[str, int] = {}
    by_page: dict[str, int] = {}
    by_day: dict[str, int] = {}
    queries: list[str] = []
    images: list[str] = []
    log_rows: list[list[str]] = []
    for a in acts:
        t = (a.get("type") or "기타").strip()
        by_type[t] = by_type.get(t, 0) + 1
        pg = page_ko.get((a.get("page") or "").strip(), (a.get("page") or "기타").strip() or "기타")
        by_page[pg] = by_page.get(pg, 0) + 1
        day = _ts(a.get("ts"), "%m-%d")
        by_day[day] = by_day.get(day, 0) + 1
        label = (a.get("label") or "").strip()
        if label and ("질의" in t or "검색" in t):
            queries.append(label)
        if label and ("이미지" in t or "분석" in t or "라벨" in t):
            images.append(label)
        log_rows.append([_ts(a.get("ts"), "%m-%d %H:%M"), t, label or "-", pg])

    # 파생 지표 — 더 다양한 통계
    active_days = len(by_day)
    peak_type, peak_type_n = max(by_type.items(), key=lambda kv: kv[1]) if by_type else ("-", 0)
    busy_day, busy_day_n = max(by_day.items(), key=lambda kv: kv[1]) if by_day else ("-", 0)
    avg_per_day = round(n / active_days, 1) if active_days else 0

    def pct(v):
        return f"{round(v / n * 100)}%" if n else "0%"

    # 통계 표(여러 개) — 유형별/일자별/화면별/로그
    type_table = {
        "columns": ["활동 유형", "횟수", "비율"],
        "rows": [[k, str(v), pct(v)] for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])]
        or [["활동 없음", "0", "0%"]],
        "caption": f"유형별 활동 ({period_label})",
    }
    day_table = {
        "columns": ["날짜", "횟수"],
        "rows": [[k, str(v)] for k, v in sorted(by_day.items())] or [["-", "0"]],
        "caption": "일자별 활동",
    }
    page_table = {
        "columns": ["사용 화면", "횟수"],
        "rows": [[k, str(v)] for k, v in sorted(by_page.items(), key=lambda kv: -kv[1])]
        or [["-", "0"]],
        "caption": "화면별 활동",
    }
    log_table = {
        "columns": ["시각", "유형", "내용", "화면"],
        "rows": log_rows[:60] or [["-", "활동 없음", "-", "-"]],
        "caption": f"활동 로그 ({min(n, 60)}건)",
    }

    stat_bullets = "\n".join(
        [
            f"- 총 활동: {n}건",
            f"- 활동한 날: {active_days}일",
            f"- 하루 평균(활동일 기준): {avg_per_day}건",
            f"- 가장 많이 한 작업: {peak_type} ({peak_type_n}회 · {pct(peak_type_n)})",
            f"- 가장 활발한 날: {busy_day} ({busy_day_n}건)",
            f"- 활동 유형 {len(by_type)}종 · 사용 화면 {len(by_page)}곳",
        ]
    )

    context = (
        f"기간: {period_label}\n총 활동 {n}건 · 활동일 {active_days}일 · 하루 평균 {avg_per_day}건\n"
        + "유형별: "
        + ", ".join(f"{k} {v}회" for k, v in by_type.items())
    )
    if queries:
        context += "\n주요 질의/검색: " + " · ".join(dict.fromkeys(queries))[:600]
    if images:
        context += "\n분석/라벨 대상: " + " · ".join(dict.fromkeys(images))[:400]

    # 보고서 유형별 본문(MOCK) — 유형마다 다른 구성/표
    if rtype == "상세 내역":
        sections = [
            {
                "heading": "1. 개요",
                "body": f"{period_label} 동안의 활동을 시간순으로 정리했습니다. 총 {n}건.",
            },
            {"heading": "2. 통계 요약", "body": stat_bullets},
        ]
        if queries:
            sections.append(
                {
                    "heading": "3. 주요 질의·검색",
                    "body": "\n".join(f"- {q}" for q in dict.fromkeys(queries))[:800],
                }
            )
        if images:
            sections.append(
                {
                    "heading": f"{len(sections) + 1}. 분석·라벨 대상",
                    "body": "\n".join(f"- {im}" for im in dict.fromkeys(images))[:600],
                }
            )
        tables = [log_table, type_table]
    elif rtype == "활동 통계":
        sections = [
            {"heading": "1. 통계 요약", "body": stat_bullets},
            {
                "heading": "2. 해석",
                "body": (
                    f"가장 많이 사용한 기능은 '{peak_type}'({pct(peak_type_n)})이며, "
                    f"'{busy_day}'에 활동이 집중되었습니다."
                    if n
                    else "기록된 활동이 없습니다. 검색·이미지 분석·문서 색인 등을 사용하면 통계가 집계됩니다."
                ),
            },
        ]
        tables = [type_table, day_table, page_table]
    else:  # 활동 요약 — 요약 + 통계 합본(가장 풍부)
        sections = [
            {
                "heading": "1. 개요",
                "body": (
                    f"{period_label} 동안 총 {n}건의 활동이 있었고, {active_days}일에 걸쳐 "
                    f"하루 평균 {avg_per_day}건을 수행했습니다."
                    if n
                    else f"{period_label} 동안 기록된 활동이 없습니다."
                ),
            },
            {"heading": "2. 핵심 지표", "body": stat_bullets},
        ]
        if queries:
            sections.append(
                {
                    "heading": "3. 주요 질의·검색",
                    "body": "\n".join(f"- {q}" for q in dict.fromkeys(queries))[:800],
                }
            )
        if images:
            sections.append(
                {
                    "heading": f"{len(sections) + 1}. 분석·라벨 대상",
                    "body": "\n".join(f"- {im}" for im in dict.fromkeys(images))[:600],
                }
            )
        sections.append(
            {
                "heading": f"{len(sections) + 1}. 종합",
                "body": (
                    f"위 활동을 바탕으로 도로 파손 데이터의 수집·분석·라벨링이 진행되었습니다. "
                    f"'{peak_type}' 작업 비중이 가장 높았습니다."
                    if n
                    else "아직 기록된 활동이 없습니다. 검색·이미지 분석·문서 색인 등을 사용하면 활동이 집계됩니다."
                ),
            }
        )
        tables = [type_table, day_table]

    # Gemini 로 본문 품질 향상(가능 시) — 통계 표는 그대로 유지
    backend = "MOCK"
    key = _gemini_key()
    if key and n:
        try:
            from google import genai

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            prompt = (
                f"다음은 사용자의 도로 유지보수 AI 플랫폼 사용 활동 로그 요약이다. 이를 분석해 한국어 "
                f"'{rtype} 보고서'를 작성하라. 활동 통계·패턴·주요 작업·인사이트를 포함하고, "
                "4~5개 섹션 '## N. 제목' 한 줄 + 본문 2~3문장 또는 '- ' 불릿으로. 머리말/맺음말 없이.\n\n"
                + context
            )
            resp = _gemini_generate(client, model="gemini-2.5-flash", contents=prompt)
            parsed = _parse_md_sections(resp.text or "")
            if parsed:
                sections = parsed
                backend = "GEMINI"
        except Exception:
            pass

    return {
        "backend": backend,
        "report_type": rtype,
        "org": f"GNSOFT · {rtype}",
        "date": "2026.6.24",
        "period": period_label,
        "title": f"내 {rtype} 보고서",
        "subtitle": f"{period_label} · 총 활동 {n}건 · 활동일 {active_days}일 · 평균 {avg_per_day}건/일",
        "sections": sections,
        "table": None,
        "tables": tables if include_chart else [],
        "sources": [f"세션 활동 로그 {n}건"],
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


def rag_get_doc(source: str, project: str = "") -> dict:
    """참고중인 파일(소스명)의 본문 청크를 돌려준다 — 파일 열람용."""
    name = (source or "").strip()
    chunks = [d["text"] for d in _active_corpus(project) if d["source"] == name]
    return {"backend": BACKEND, "source": name, "found": bool(chunks), "chunks": chunks}


# 파일명 키워드 → 추천 질문.
_SUGGEST_MAP = [
    ("포트홀", "심각한 포트홀은 며칠 안에 보수해야 해?"),
    ("균열", "거북등 균열은 어떻게 보수해?"),
    ("시설물", "가드레일 점검 주기는 어떻게 돼?"),
    ("우천", "우천 시 쓸 수 있는 긴급 보수 공법은?"),
    ("예산", "지역별 도로보수 예산 집행률은 어때?"),
    ("cctv", "CCTV로 어떤 이상행동을 탐지해?"),
]


def _suggest_for(source: str) -> str:
    low = source.lower()
    for kw, q in _SUGGEST_MAP:
        if kw in low:
            return q
    base = source.rsplit(".", 1)[0]
    return f"‘{base}’ 문서의 핵심 내용은?"


def rag_list_files(project: str = "") -> dict:
    """현재 색인된 참고 파일 목록 + 실제 청크 수(하이브리드 엔진 기준) + 추천 질문."""
    from . import rag_engine

    corpus = _active_corpus(project)
    order: list[str] = []
    for d in corpus:
        if d["source"] not in order:
            order.append(d["source"])
    counts = rag_engine.chunk_counts(corpus)  # 실제 청킹된 청크 수
    files = [{"source": s, "chunks": counts.get(s, 1)} for s in order]
    # 참고 파일에 따라 달라지는 추천 질문(중복 제거, 최대 4개).
    suggestions: list[str] = []
    for s in order:
        q = _suggest_for(s)
        if q not in suggestions:
            suggestions.append(q)
    return {"backend": BACKEND, "files": files, "suggestions": suggestions[:4]}


def rag_remove_doc(source: str, project: str = "") -> dict:
    """참고중인 파일을 색인에서 삭제(이후 검색 근거에서 제외)."""
    name = (source or "").strip()
    udocs = _udocs(project)
    # 사용자 문서면 제거, 샘플이면 제외 목록에 등록.
    before = len(udocs)
    udocs[:] = [d for d in udocs if d["source"] != name]
    if len(udocs) == before:
        _removed(project).add(name)
    corpus = _active_corpus(project)
    return {
        "backend": BACKEND,
        "removed": name,
        "source_count": len({d["source"] for d in corpus}),
        "chunk_count": len(corpus),
        "message": f"‘{name}’ 문서를 색인에서 삭제했습니다",
    }


def rag_reset(project: str = "") -> dict:
    """전체 초기화 — 이 프로젝트의 참고 파일을 비운다(샘플 토글 OFF)."""
    _udocs(project).clear()
    _removed(project).clear()
    _samples_on_by_project[_pkey(project)] = False
    return {
        "backend": BACKEND,
        "indexed": True,
        "source_count": 0,
        "chunk_count": 0,
        "message": "전체 초기화 — 참고 파일 0개 (샘플 토글을 켜면 샘플 복원)",
    }


def rag_set_samples(on: bool, project: str = "") -> dict:
    """샘플 점검 문서 포함/제외(토글). 켜면 샘플이 참고 파일에 다시 들어간다."""
    _samples_on_by_project[_pkey(project)] = bool(on)
    if on:
        removed = _removed(project)
        for d in _SAMPLE_DOCS:
            removed.discard(d["source"])
    corpus = _active_corpus(project)
    return {
        "backend": BACKEND,
        "samples_on": _samples_on(project),
        "source_count": len({d["source"] for d in corpus}),
        "chunk_count": len(corpus),
        "message": "샘플 문서를 포함했습니다" if on else "샘플 문서를 제외했습니다",
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


# ────────────────────────────────────────────────────────────────────
# 9. 공공데이터포털(data.go.kr) 연계 — "관련 통계를 보여줘"
#    여러 데이터셋을 설정만으로 늘리는 확장 구조는 backend/pubdata/ 패키지 참고.
#    (레지스트리 → 어댑터 → SQLite 통합 저장소 → 통합 조회)
#    여기서는 그 통계 결과에 Gemini 자연어 요약을 얹는다.
# ────────────────────────────────────────────────────────────────────
def _summarize_pubdata(kw: str, domain: str, stats: dict) -> tuple[str, str]:
    """통계 시리즈를 자연어로 요약. Gemini 우선, 무키/실패 시 템플릿. (summary, backend)"""
    labels = stats["labels"]
    values = stats["values"]
    peak_i = max(range(len(values)), key=lambda i: values[i])
    low_i = min(range(len(values)), key=lambda i: values[i])
    facts = (
        f"주제: {domain}. 지표: {stats['title']} (단위 {stats['unit']}). "
        f"최고 {labels[peak_i]}={values[peak_i]}, 최저 {labels[low_i]}={values[low_i]}, "
        f"합계 {sum(values)}, 평균 {round(sum(values) / len(values), 1)}."
    )
    key = _gemini_key()
    if key:
        try:
            from google import genai

            client = genai.Client(api_key=key, http_options={"timeout": 20000})
            prompt = (
                "너는 공공데이터 분석 도우미다. 아래 통계 요약 수치만 근거로, "
                "도로·시설 유지보수 담당자에게 도움이 되도록 한국어 2~3문장으로 "
                "핵심 경향과 시사점을 간결히 설명하라. 수치를 지어내지 마라.\n\n"
                f"질문 키워드: {kw}\n{facts}"
            )
            resp = _gemini_generate(client, model="gemini-2.5-flash", contents=prompt)
            text = (resp.text or "").strip()
            if text:
                return text, "GEMINI"
        except Exception:
            pass
    return (
        f"‘{kw}’ 관련 {domain} 데이터를 보면, {labels[peak_i]}({stats['unit']} {values[peak_i]})에 "
        f"가장 높고 {labels[low_i]}에 가장 낮습니다. 합계 {sum(values)}{stats['unit']}, "
        f"평균 {round(sum(values) / len(values), 1)}{stats['unit']} 수준입니다.",
        "MOCK",
    )


def pubdata_search(keyword: str) -> dict:
    """공공데이터포털 연계 검색 — 통합 저장소 통계 + 데이터셋 목록 + 자연어 요약.

    통계 시리즈는 backend/pubdata 통합 저장소(SQLite)에서 조회한다. 서비스키가
    있으면 실 API 로 적재(live=True), 없으면 시드(stats.sample=True)로 동작한다.
    """
    from . import pubdata

    data = pubdata.service.build(keyword)
    summary, summary_backend = _summarize_pubdata(data["keyword"], data["domain"], data["stats"])
    return {
        "backend": BACKEND,
        **data,
        "summary": summary,
        "summary_backend": summary_backend,
        "message": f"‘{data['keyword']}’ 관련 공공데이터 {data['dataset_matched']}건과 통계를 찾았습니다.",
    }


def pubdata_catalog() -> dict:
    """등록된 전체 공공데이터셋 카탈로그(현황)."""
    from . import pubdata

    return pubdata.service.catalog()


# ────────────────────────────────────────────────────────────────────
# 10. AI 에이전트 업무 자동화 — "업무 절차를 자동으로 추천해줘"
#    자연어 목표 → 단계별 업무 절차(각 단계를 플랫폼 기능에 매핑) 설계.
#    Gemini(tool 카탈로그 기반) 우선, 무키/429 시 규칙 기반 폴백.
# ────────────────────────────────────────────────────────────────────
# 에이전트가 각 단계에 배정할 수 있는 플랫폼 기능(도구).
_AGENT_TOOLS = {
    "query": {"label": "자연어 질의", "icon": "☰", "page": "query.html"},
    "rag": {"label": "RAG 문서 검색", "icon": "⌕", "page": "rag.html"},
    "pubdata": {"label": "공공데이터 통계", "icon": "◫", "page": "pubdata.html"},
    "labeling": {"label": "이미지 분석·라벨링", "icon": "⌗", "page": "labeling.html"},
    "report": {"label": "요약·보고서 생성", "icon": "⇱", "page": "report.html"},
}


def _agent_route(tool: str, q: str = "") -> str:
    """단계의 도구 → 딥링크 URL(검색어가 있으면 ?q= 로 프리필)."""
    page = _AGENT_TOOLS.get(tool, _AGENT_TOOLS["query"])["page"]
    if q and tool in ("query", "rag", "pubdata"):  # ?q= 자동검색 지원 페이지
        from urllib.parse import quote

        return f"{page}?q={quote(q)}"
    return page


def _agent_step(raw: dict, n: int) -> dict:
    """LLM/폴백 단계(dict) → 프론트 계약(번호·도구라벨·아이콘·라우트) 정규화."""
    tool = raw.get("tool") if raw.get("tool") in _AGENT_TOOLS else "query"
    meta = _AGENT_TOOLS[tool]
    q = (raw.get("q") or "").strip()
    return {
        "n": n,
        "title": (raw.get("title") or "").strip() or f"{meta['label']} 단계",
        "tool": tool,
        "tool_label": meta["label"],
        "icon": meta["icon"],
        "why": (raw.get("why") or "").strip(),
        "q": q,
        "route": _agent_route(tool, q),
    }


def _agent_plan_fallback(goal: str) -> dict:
    """규칙 기반 절차 설계(무키/실패 시). 목표 키워드로 관련 단계를 조립."""
    low = goal.lower()
    steps: list[dict] = []
    # 상황 이해는 공통 첫 단계.
    steps.append(
        {
            "title": "상황·용어 파악하기",
            "tool": "query",
            "why": "목표와 관련한 개념·기준을 먼저 확인",
            "q": goal,
        }
    )
    if any(k in low for k in ("포트홀", "파손", "균열", "이미지", "사진", "현장", "탐지")):
        steps.append(
            {
                "title": "현장 이미지 라벨링",
                "tool": "labeling",
                "why": "도로 파손/포트홀을 탐지해 근거 이미지 확보",
            }
        )
    steps.append(
        {
            "title": "관련 규정·기준 검색",
            "tool": "rag",
            "why": "보수 기한·점검 주기 등 근거 문서 확인",
            "q": goal,
        }
    )
    if any(k in low for k in ("통계", "현황", "건수", "지역", "추이", "데이터")):
        steps.append(
            {
                "title": "공공데이터 통계 확인",
                "tool": "pubdata",
                "why": "지역·기간별 통계로 규모 파악",
                "q": goal,
            }
        )
    steps.append(
        {"title": "결과 보고서 생성", "tool": "report", "why": "처리 결과를 문서로 정리·공유"}
    )
    return {
        "summary": f"‘{goal}’ 목표를 {len(steps)}단계로 처리합니다. 각 단계에서 해당 화면으로 이동해 실행하세요.",
        "steps": steps,
    }


def _agent_plan_gemini(goal: str, key: str) -> dict | None:
    """Gemini로 절차 설계(JSON). 실패 시 None → 폴백."""
    try:
        from google import genai

        client = genai.Client(api_key=key, http_options={"timeout": 20000})
        tools_desc = "\n".join(f"- {t}: {m['label']}" for t, m in _AGENT_TOOLS.items())
        prompt = (
            "너는 도로 유지보수·시설점검 업무지원 플랫폼의 '업무 자동화 에이전트'다. "
            "사용자 목표를 달성할 업무 절차를 3~5단계로 설계하라. 각 단계는 아래 기능(tool) "
            "중 하나에 매핑한다:\n" + tools_desc + "\n\n"
            "반드시 아래 JSON만 출력(코드펜스·설명 금지):\n"
            '{"summary":"한줄요약","steps":[{"title":"단계명","tool":"rag",'
            '"why":"이 단계가 필요한 이유","q":"검색어(query/rag/pubdata일 때만, 없으면 빈칸)"}]}\n\n'
            f"목표: {goal}"
        )
        resp = _gemini_generate(client, model="gemini-2.5-flash", contents=prompt)
        data = _extract_json(resp.text or "")
        if data and isinstance(data.get("steps"), list) and data["steps"]:
            return data
    except Exception:
        pass
    return None


def agent_plan(goal: str) -> dict:
    """자연어 목표 → 단계별 업무 절차(플랫폼 기능 매핑). Gemini 우선, 폴백 보장."""
    g = (goal or "").strip()
    if not g:
        return {"backend": BACKEND, "goal": "", "summary": "목표를 입력해주세요.", "steps": []}
    key = _gemini_key()
    plan = _agent_plan_gemini(g, key) if key else None
    backend = "GEMINI"
    if not plan:
        plan = _agent_plan_fallback(g)
        backend = "MOCK"
    steps = [_agent_step(s, i + 1) for i, s in enumerate(plan["steps"][:6])]
    return {
        "backend": backend,
        "goal": g,
        "summary": (plan.get("summary") or "").strip() or f"‘{g}’ 처리 절차입니다.",
        "steps": steps,
    }


def _extract_json(text: str) -> dict | None:
    """LLM 응답에서 첫 JSON 객체를 관대하게 추출(코드펜스·잡텍스트 허용)."""
    s = (text or "").strip()
    if not s:
        return None
    start = s.find("{")
    end = s.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(s[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
