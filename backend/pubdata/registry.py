"""데이터셋 레지스트리 — 데이터셋 하나 = 설정 하나.

새 공공데이터를 늘리려면 여기 DATASETS 에 항목을 추가하면 된다.
(코드 수정 없이) store 에 적재되고, 도메인 검색·통계·시각화에 자동 포함된다.

각 항목 필드
    id        고유 식별자
    domain    화면에서 묶는 도메인명
    name      데이터셋 정식 명칭(포털 표기)
    provider  제공기관
    category  분류 태그
    fmt       배포 형식(JSON/CSV 등)
    dim       통계 차원: "period"(기간) 또는 "region"(지역)
    unit      값 단위
    chart_title 차트 제목
    seed      시드(시연/폴백)용 [(키, 값), ...]
    live      실 API 설정 — endpoint/params/mapping. 미확정이면 None.
              (public-data-finder 조사 결과를 채우면 실데이터 수집으로 전환)
"""

from __future__ import annotations

# 도메인 매칭 키워드 — 자연어 검색어를 도메인에 연결.
DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "도로 파손·포트홀": ("포트홀", "도로", "파손", "균열", "노면", "보수"),
    "공공 CCTV·이상행동": ("cctv", "이상행동", "영상", "관제", "방범"),
    "시설물 안전점검": ("시설물", "안전점검", "교량", "터널", "옹벽", "점검"),
    "교통·사고": ("교통", "사고", "차량", "속도", "다발"),
    "기상·도로결빙": ("기상", "날씨", "강수", "적설", "결빙", "기온"),
}

DEFAULT_DOMAIN = "도로 파손·포트홀"


DATASETS: list[dict] = [
    {
        "id": "road_pothole_reports",
        "domain": "도로 파손·포트홀",
        "name": "행정안전부_도로 파손 신고(안전신문고) 접수 현황",
        "provider": "행정안전부",
        "category": "안전",
        "fmt": "JSON",
        "dim": "period",
        "unit": "건",
        "chart_title": "월별 포트홀 신고 건수 (최근 12개월)",
        "seed": [
            ("7", 180),
            ("8", 165),
            ("9", 150),
            ("10", 190),
            ("11", 240),
            ("12", 310),
            ("1", 420),
            ("2", 480),
            ("3", 520),
            ("4", 410),
            ("5", 300),
            ("6", 220),
        ],
        "insight": "해빙기(2~4월) 신고 급증 — 동결·융해 반복이 주원인. 봄철 보수 인력 선제 배치 필요.",
        "live": None,
    },
    {
        "id": "road_maintenance",
        "domain": "도로 파손·포트홀",
        "name": "국토교통부_도로보수 유지관리 실적",
        "provider": "국토교통부",
        "category": "도로",
        "fmt": "CSV",
        "dim": "region",
        "unit": "건",
        "chart_title": "지역별 도로보수 실적",
        "seed": [
            ("서울", 3200),
            ("경기", 5400),
            ("인천", 1600),
            ("대전", 1200),
            ("부산", 2100),
            ("대구", 1800),
            ("광주", 1100),
        ],
        "insight": "경기·서울에 보수 물량 집중 — 교통량·노후도와 비례.",
        "live": None,
    },
    {
        "id": "cctv_install",
        "domain": "공공 CCTV·이상행동",
        "name": "행정안전부_전국 CCTV 설치 현황",
        "provider": "행정안전부",
        "category": "안전",
        "fmt": "CSV",
        "dim": "region",
        "unit": "천 대",
        "chart_title": "지역별 공공 CCTV 설치 대수",
        "seed": [
            ("서울", 88),
            ("경기", 132),
            ("인천", 41),
            ("대전", 33),
            ("부산", 47),
            ("대구", 38),
            ("광주", 25),
        ],
        "insight": "경기·서울에 설치 집중. 관제 인력 대비 카메라가 많아 이상행동 자동탐지 수요가 큼.",
        # CSV 파일데이터 배선. 주소(시군구)별 카메라대수 합산.
        # 참고: https://www.data.go.kr/data/15013094/standard.do
        "live": {
            "type": "csv",
            "endpoint": "https://file.localdata.go.kr/file/cctv_info/info",
            "encoding": "cp949",
            "mapping": {"dim": "소재지지번주소", "value": "카메라대수", "dim_transform": "sigungu"},
            "aggregate": "sum",
            "note": "현재 직링크가 403(리퍼러/세션 필요)일 수 있음. 컬럼명은 실제 CSV로 확인 후 조정. "
            "접근 불가 시 자동으로 시드 폴백.",
        },
    },
    {
        "id": "facility_grade",
        "domain": "시설물 안전점검",
        "name": "국토안전관리원_시설물 안전등급 현황",
        "provider": "국토안전관리원",
        "category": "안전",
        "fmt": "CSV",
        "dim": "region",
        "unit": "%",
        "chart_title": "시설물 안전등급 분포",
        "seed": [("A", 22), ("B", 48), ("C", 24), ("D", 5), ("E", 1)],
        "insight": "C등급 이하가 30% — 우선 점검·보수 대상. D·E는 즉시 정밀안전진단 연계 필요.",
        "live": None,
    },
    {
        # 실 API 배선 완료(키 있으면 실데이터). 지자체별 사고다발지역 오픈API.
        # 참고: https://www.data.go.kr/data/15057467/openapi.do (도로교통공단, B552061)
        "id": "traffic_accident",
        "domain": "교통·사고",
        "name": "도로교통공단_지자체별 교통사고 다발지역",
        "provider": "도로교통공단",
        "category": "교통",
        "fmt": "JSON",
        "dim": "region",
        "unit": "건",
        "chart_title": "지자체별 교통사고 다발지역 발생건수",
        "seed": [
            ("서울 강남구", 42),
            ("서울 송파구", 33),
            ("경기 수원", 38),
            ("경기 성남", 29),
            ("부산 부산진구", 27),
            ("대구 달서구", 24),
            ("대전 서구", 19),
        ],
        "insight": "도심 상업지구에 사고 다발지 집중. 사고 다발지와 도로 파손지 상관 분석이 유효.",
        # searchYearCd·siDo·guGun 필수. 지점 단위 응답을 aggregate=sum 으로 지역 합산.
        "live": {
            "endpoint": "http://apis.data.go.kr/B552061/frequentzoneLg/getRestFrequentzoneLg",
            "params": {
                "searchYearCd": "2023",
                "siDo": "11",
                "guGun": "680",
                "numOfRows": "100",
                "pageNo": "1",
                "type": "json",
            },
            "rows_path": "response.body.items.item",
            "mapping": {"dim": "sido_sgg_nm", "value": "occrrnc_cnt"},
            "aggregate": "sum",
            "note": "인코딩 서비스키 필요(apis.data.go.kr). siDo/guGun 은 법정동 코드 — "
            "지역 비교엔 코드별로 여러 번 호출해 누적하는 확장이 필요.",
        },
    },
    {
        "id": "weather_precip",
        "domain": "기상·도로결빙",
        "name": "기상청_지상 기상관측(월별 강수·기온)",
        "provider": "기상청",
        "category": "기상",
        "fmt": "JSON",
        "dim": "period",
        "unit": "mm",
        "chart_title": "월별 강수량 (도로결빙·침수 위험 참고)",
        "seed": [
            ("1", 30),
            ("2", 35),
            ("3", 55),
            ("4", 80),
            ("5", 100),
            ("6", 150),
            ("7", 380),
            ("8", 320),
            ("9", 160),
            ("10", 60),
            ("11", 50),
            ("12", 25),
        ],
        "insight": "여름(7~8월) 강수 집중 — 침수·노면 손상 위험기. 겨울 저강수+저온은 결빙 위험.",
        # ASOS 일자료 배선. 일강수(sumRn)를 관측일(tm)에서 월 추출해 합산 → 월별 강수량.
        # 참고: https://www.data.go.kr/data/15059093/openapi.do (기상청, 1360000)
        "live": {
            "endpoint": "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList",
            "params": {
                "dataType": "JSON",
                "dataCd": "ASOS",
                "dateCd": "DAY",
                "startDt": "20250101",
                "endDt": "20251231",
                "stnIds": "108",  # 서울 지점
                "numOfRows": "400",
                "pageNo": "1",
            },
            "rows_path": "response.body.items.item",
            "mapping": {"dim": "tm", "value": "sumRn", "dim_transform": "month"},
            "aggregate": "sum",
            "note": "서비스키 필요. tm(관측일)에서 월 추출 후 sumRn(일강수) 합산. "
            "빈 강수일(공백)은 자동 제외. stnIds 로 지점 변경 가능.",
        },
    },
]


def datasets_for(domain: str) -> list[dict]:
    """도메인에 속한 데이터셋 목록."""
    return [d for d in DATASETS if d["domain"] == domain]


def by_id(dataset_id: str) -> dict | None:
    for d in DATASETS:
        if d["id"] == dataset_id:
            return d
    return None


def match_domain(keyword: str) -> str:
    """자연어 검색어 → 도메인. 매칭 없으면 기본 도메인."""
    low = (keyword or "").lower()
    for domain, kws in DOMAIN_KEYWORDS.items():
        if any(k in low for k in kws):
            return domain
    return DEFAULT_DOMAIN
