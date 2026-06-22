# GNSoft AI 플랫폼 (web)

지엔소프트 AI 업무 지원 플랫폼의 프론트엔드(HTML/CSS/JS 멀티페이지). 자연어 질의·RAG 검색·
이미지 라벨링·보고서·데이터 관리 화면이 `backend`(FastAPI)의 `/api/*` 와 연결돼 동작합니다.

> 프론트엔드의 하드코딩 mock은 제거되었고, 화면 데이터는 모두 백엔드 API에서 받아옵니다.
> 백엔드 구현은 현재 MOCK(`backend/services.py`)이며, RAG/라벨링 실제 로직은
> `prototypes/`의 코드로 추후 교체합니다.

## 시작하기 (통합 서버 — 권장)

```bash
uv pip install -e ".[web]"          # 또는: pip install fastapi "uvicorn[standard]"
uvicorn backend.app:app --reload    # 저장소 루트(llm-job-support/)에서 실행
# http://localhost:8000  접속  → 메인 대시보드
```

통합 서버가 `web/` UI와 `/api/*` 를 같은 주소에서 함께 제공합니다.

## 정적으로만 열기 (API 없음)

`index.html`을 브라우저로 직접 열거나 `python -m http.server` 로 띄울 수도 있습니다.
이 경우 API 호출이 실패하면 화면은 HTML 기본값으로 폴백합니다(분석·검색 등 동적 기능은 비활성).

## 디렉터리 구조

```
.
├── index.html              # 진입점 — pages/dashboard.html 로 리다이렉트
├── pages/                  # 페이지별 HTML
│   ├── dashboard.html      # 메인 대시보드
│   ├── query.html          # 자연어 질의
│   ├── rag.html            # RAG 공공데이터 검색
│   ├── labeling.html       # 이미지 분석·라벨링
│   ├── report.html         # 요약·보고서 생성
│   └── data.html           # 데이터 관리
└── assets/
    ├── css/                # common.css + 페이지별 스타일
    └── js/                 # common.js + 페이지별 스크립트
```

## 페이지 ↔ 리소스 매핑

| 페이지 | HTML | CSS | JS |
| --- | --- | --- | --- |
| 메인 대시보드 | `pages/dashboard.html` | `assets/css/dashboard.css` | `assets/js/dashboard.js` |
| 자연어 질의 | `pages/query.html` | `assets/css/query.css` | `assets/js/query.js` |
| RAG 검색 | `pages/rag.html` | `assets/css/rag.css` | `assets/js/rag.js` |
| 이미지 라벨링 | `pages/labeling.html` | `assets/css/labeling.css` | `assets/js/labeling.js` |
| 보고서 생성 | `pages/report.html` | `assets/css/report.css` | `assets/js/report.js` |
| 데이터 관리 | `pages/data.html` | `assets/css/data.css` | `assets/js/data.js` |

모든 페이지는 `assets/css/common.css` 와 `assets/js/common.js` 를 공통으로 사용합니다.
