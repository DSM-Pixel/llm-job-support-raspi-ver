---
name: public-data-rag
description: 공공데이터포털(data.go.kr) API를 찾아 → 어댑터로 래핑 → 캐시/인덱싱 → RAG 질의응답에 붙이는 전체 절차. "공공데이터 ~를 RAG에 넣어줘", "data.go.kr에서 ~ 데이터 연동" 요청 시 사용.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebFetch
  - WebSearch
  - AskUserQuestion
---

# /public-data-rag

공공데이터 소스 1개를 찾아서 우리 RAG 파이프라인(문서 선택 + 자연어 질의응답)에 붙일 때 이 절차를 따른다.
시작 전에 `checklist.md`(이 폴더)를 읽고 키 발급·트래픽·라이선스 항목을 먼저 확인한다.

## 0. 입력 수집

사용자가 안 알려줬으면 `AskUserQuestion`으로:
1. **도메인/키워드** (예: 도로 포장상태, 교통사고 통계, 기상)
2. **용도**: RAG 코퍼스에 문서로 추가 / 통계 질의응답 / 대시보드 표시
3. **키 보유 여부**: `DATA_GO_KR_KEY` 발급·활용신청 완료?

## 1. API 찾기

- `WebFetch`/`WebSearch`로 data.go.kr에서 후보를 직접 확인한다. **가짜 endpoint를 지어내지 말 것.**
- 참고 레퍼런스: https://github.com/yybmion/public-apis-4Kr (한국 공공 API 모음)
- 후보마다 확인: 제공기관 / 인증키 방식(Encoded·Decoded) / 응답 포맷(JSON·XML) / 트래픽 제한 / 공공누리 유형.
- CSV 일괄 다운로드 자료면 API 대신 파일을 받아 pandas로 읽는 쪽을 추천한다.
- 조사가 길어지면 `public-data-finder` 서브에이전트에 위임.

## 2. 어댑터로 래핑

- 위치: `backend/pubdata/adapters.py`에 어댑터 추가 + `registry.py`에 등록. **기존 어댑터 패턴을 먼저 읽고 똑같이 따른다.**
- 키는 `os.environ["DATA_GO_KR_KEY"]` (Decoded). 하드코딩 금지.
- `requests.get(..., timeout=10)` + `raise_for_status()` + 응답 구조(`response.body.items.item` 류) 파싱까지 어댑터가 책임.
- 실패/키 없음 시 예외를 삼키지 말고 호출부가 MOCK 폴백을 탈 수 있게 명확한 예외를 던진다.

## 3. 캐싱 + 인덱싱

- 원본 응답은 `backend/pubdata/store.py` 경유로 `backend/storage/pubdata.db`에 저장 (수집 시각·출처 URL·공공누리 유형 포함). 재호출 전 캐시 먼저 확인 — 일일 트래픽 제한 보호.
- 레코드를 RAG 문서로 변환: 항목 1건 = 문서 1건, 제목 + 본문 텍스트 + 메타(출처, 날짜, 지역 등). 변환은 `backend/pubdata/ingest.py` 패턴.
- 인덱싱은 `backend/rag_engine.py` 재사용 (BM25 + dense 하이브리드, 청크 400자/overlap 60). 새 검색 엔진 만들지 말 것 — `.claude/rules/rag.md` 준수.

## 4. 질의응답 연결

- `/api/rag/*` 라우트(`backend/app.py`)와 서비스 계층을 통해 노출. 프론트는 `web/pages/rag.html`·`pubdata.html`이 이미 있으니 **기존 화면에 연결**한다.
- 답변에는 출처 인용 마크(`[doc1]`)와 데이터 출처(기관명·공공누리 유형)를 반드시 표시.
- Gemini 키가 없어도 어휘 폴백으로 검색이 동작하는지 확인.

## 5. 검증 (끝내기 전 필수)

```bash
uv run pytest                          # 어댑터 mock 테스트 통과
uvicorn backend.app:app --reload       # 띄워서
# → rag.html 에서 "…에 대해 알려줘" 실제 질의 1회 성공 확인
```

- 검증 시나리오: "공공데이터포털 기반으로 관련 통계를 보여줘"가 새 데이터로 답하는지.
- 끝나면 추가한 데이터셋 이름·출처·라이선스를 `docs/notes/공공데이터_API_연계_조사.md`에 한 줄 추가.

## 하지 말 것

- 활용신청 승인 전 API를 코드에 박아두고 "동작한다"고 말하지 말 것 (미승인 키는 401/403).
- 트래픽 제한 무시하고 루프에서 전체 페이지를 즉시 수집하지 말 것 — 필요한 만큼만, 캐시 우선.
- 공공누리 유형 확인 없이 데이터를 코퍼스에 넣지 말 것 (`checklist.md` 참고).
