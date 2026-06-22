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
# 3. RAG 검색 (MOCK)  실제 연동: prototypes/rag-search _hybrid_search + respond
# ────────────────────────────────────────────────────────────────────
_RAG_DOCS = [
    {
        "source": "포트홀_보수_기준.md",
        "score": 0.94,
        "text": "심각(상) 등급은 발견 즉시 24시간 이내 긴급 보수. 보통(중) 등급은 7일 이내 보수.",
    },
    {
        "source": "포트홀_보수_기준.md",
        "score": 0.90,
        "text": "심각(상): 지름 30cm 이상 또는 깊이 5cm 이상. 차량 손상 우려.",
    },
    {
        "source": "도로_균열_점검.md",
        "score": 0.71,
        "text": "균열 폭 3mm 이상이면 보수 대상으로 기록한다. 거북등 균열은 면적을 산정하여 보수 물량을 추정한다.",
    },
]


def rag_search(query: str, top_k: int = 4) -> dict:
    """하이브리드 RAG 검색 + 근거 기반 답변. (MOCK)"""
    q = (query or "").strip()
    sources = _RAG_DOCS[:top_k]
    answer = (
        f"질문 <b>“{q}”</b> 에 대해 색인된 문서를 검색했습니다. "
        "<b>심각(상) 등급은 발견 즉시 24시간 이내 긴급 보수</b> 대상이며 <sup>1</sup>, "
        "보통(중)은 7일 이내, 경미(하)는 정기 보수 주기에 포함해 처리합니다. <sup>2</sup>"
    )
    return {
        "backend": BACKEND,
        "query": q,
        "answer": answer,
        "confidence": 0.93,
        "method": "하이브리드 RAG · RRF",
        "elapsed": "0.41s",
        "top_k": len(sources),
        "chunks": 14,
        "sources": sources,
    }


def rag_index(sources: list[str] | None = None, use_samples: bool = True) -> dict:
    """문서 색인 빌드. (MOCK)"""
    names = sources or []
    source_count = (4 if use_samples else 0) + len(names)
    return {
        "backend": BACKEND,
        "indexed": True,
        "source_count": max(source_count, 1),
        "chunk_count": max(source_count, 1) * 5,
        "message": f"색인됨 — 소스 {max(source_count, 1)}개 · 청크 {max(source_count, 1) * 5}개",
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


# ────────────────────────────────────────────────────────────────────
# 5. 보고서 생성 (MOCK)
# ────────────────────────────────────────────────────────────────────
def generate_report(
    report_type: str = "현황 분석", period: str = "최근 3년", sources: list[str] | None = None
) -> dict:
    """선택 조건으로 보고서 미리보기를 생성. (MOCK)"""
    clean = re.sub(r"[▥▤▢]", "", report_type).strip() or "현황 분석"
    return {
        "backend": BACKEND,
        "title": f"도로 파손 {clean} 보고서",
        "subtitle": f"생성일 2026.6.22 · 소스 {len(sources or []) or 3}개 · {period}",
        "summary": (
            "최근 도로 파손 신고는 증가 추세이며 수도권 비중이 가장 높습니다. "
            "Vision AI 검수 결과 심각(상) 등급 비율은 전 분기 대비 소폭 상승했고, "
            "보수 예산 집행률은 지역별 편차가 큽니다. 심각 등급은 24시간 이내 긴급 보수, "
            "보통 등급은 7일 이내 처리 기준 적용을 권고합니다."
        ),
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
    """색인 초기화. (MOCK)"""
    return {
        "backend": BACKEND,
        "indexed": False,
        "source_count": 0,
        "chunk_count": 0,
        "message": "색인을 초기화했습니다 — 소스 0개",
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
