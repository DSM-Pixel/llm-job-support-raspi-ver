---
description: 4대 데모 시나리오가 end-to-end로 도는지 통합 점검 (포트홀 탐지 / 공공데이터 통계 / 요약 보고서 / 업무 절차 추천)
allowed-tools: Bash, Read, Glob, Grep
---

4대 데모 시나리오가 실제로 end-to-end(프론트 → API → 결과)로 도는지 점검하고 결과를 표로 보고해라. 인자: `$ARGUMENTS` (특정 시나리오 번호만 점검 가능, 비면 전체)

## 준비

1. 통합 서버가 안 떠 있으면 백그라운드로 띄운다: `./run_web.sh` (또는 `uv run uvicorn backend.app:app --port 8000`).
2. `curl http://localhost:8000/` 200 확인.

## 4대 시나리오

각 시나리오마다: 해당 API를 curl로 실제 호출 → 응답 스키마·내용 확인 → 대응 프론트 페이지가 그 API를 fetch하는지 JS에서 확인.

| # | 시나리오 | API 경로 (backend/app.py에서 실제 경로 확인) | 프론트 |
|---|-----------|---------------------------------------------|--------|
| 1 | "포트홀 영역을 찾아줘" | 라벨링/탐지 API (이미지 업로드 → 박스/마스크) | `web/pages/labeling.html` |
| 2 | "공공데이터포털 기반으로 관련 통계를 보여줘" | RAG 검색/pubdata API | `web/pages/rag.html`, `pubdata.html` |
| 3 | "검색 결과를 요약해서 보고서로 만들어줘" | 요약/보고서 API | `web/pages/report.html` |
| 4 | "업무 절차를 자동으로 추천해줘" | 질의/에이전트 API | `web/pages/query.html`, `agent.html` |

## 판정 기준

- **PASS**: HTTP 200 + 의미 있는 응답 (MOCK이면 MOCK이라고 명기 — `"backend": "MOCK"` 필드 확인)
- **PARTIAL**: API는 돌지만 프론트 연동 안 됨 (또는 그 반대)
- **FAIL**: 5xx / 라우트 없음 / 예외

이미지가 필요한 시나리오 1은 `prototypes/image-understanding/_samples/`의 샘플 이미지를 사용한다.
Gemini 키가 없는 환경에서는 MOCK 폴백으로 도는지가 판정 기준 (폴백 실패 = FAIL).

## 보고 형식

```
| 시나리오 | 판정 | 백엔드 | 비고 |
|----------|------|--------|------|
| 1. 포트홀 탐지 | PASS | REAL(YOLO) | ... |
| 2. 공공데이터 통계 | PARTIAL | MOCK | rag.html fetch 미연결 |
...
```

마지막에 FAIL/PARTIAL 항목의 원인 파일 경로와 다음 액션을 한 줄씩 제안한다. **수정은 하지 말고 점검·보고만** — 수정은 사용자가 시킬 때.
