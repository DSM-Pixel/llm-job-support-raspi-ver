# backend — 통합 웹 플랫폼 API

`web/` 정적 UI를 서빙하고 `/api/*` 엔드포인트를 제공하는 FastAPI 앱.

## 실행

```bash
uv sync --extra web
# 루트에서
./run_web.sh        # macOS/Linux/Git Bash
./run_web.ps1       # Windows PowerShell
# 또는 직접
.venv/Scripts/python -m uvicorn backend.app:app --reload
```

기본 주소: http://127.0.0.1:8000

## 구조

| 파일 | 역할 |
|------|------|
| `app.py` | FastAPI 진입점, 라우팅, `web/` 정적 서빙 |
| `services.py` | 서비스 계층 (Gemini 연동·RAG·보고서·대시보드 집계) |
| `yolo_service.py` | YOLO 도로파손 탐지 추론 |
| `ml/finetuning/` | YOLO 학습·평가 스크립트 |

> 키가 없거나 한도 소진 시에는 `BACKEND = "MOCK"` 폴백으로 가짜 데이터를 돌려준다.

## API 엔드포인트 (24개)

| 분류 | 엔드포인트 |
|------|-----------|
| 상태 | `GET /api/health`, `GET /api/dashboard` |
| 질의 | `POST /api/query`, `POST /api/ask/context`, `POST /api/ask/image` |
| RAG | `POST /api/rag/search · index · web-search · reset · remove · samples`, `GET /api/rag/doc · files` |
| 라벨링 | `POST /api/labeling/detect · detect-image · analyze-image · save`, `GET /api/labeling/model` |
| 보고서 | `POST /api/report · report/web · report/from-rag · report/activity · report/revise` |
| 데이터 | `GET /api/datasets`, `POST /api/datasets/upload` |
