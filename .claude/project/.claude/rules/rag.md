# 규칙: RAG 파트 (rag)

> 적용 대상: `backend/rag_engine.py`, `backend/pubdata/**`, `prototypes/rag-search/**` 등 RAG 관련 코드.

## 검색은 하이브리드가 디폴트

- **BM25(어휘) + dense(의미) 하이브리드 + RRF 융합**이 기본이다. dense 단독 검색을 새로 만들지 말 것.
- 기준 구현은 `backend/rag_engine.py` — BM25는 순수 numpy Okapi 직접 구현, 융합은 RRF. 새 검색 기능은 이 엔진을 재사용/확장한다 (프로토타입에서 검증 후 이식하는 흐름 유지).

## 한국어 임베딩

- dense 임베딩은 **Gemini `gemini-embedding-001`** (키 있을 때) → 키 없음/429 시 **문자 n-gram 어휘 임베딩 폴백** — 이 폴백 체인을 깨지 말 것. 어떤 환경에서도 검색은 항상 동작해야 한다.
- 로컬 임베딩 모델 도입 시 한국어 지원 모델만: `BAAI/bge-m3`, `intfloat/multilingual-e5`, `nlpai-lab/KURE-v1` 계열. 단, **RPi5에서는 로컬 임베딩 상주 금지** — API 우선.
- BM25 토크나이저는 한국어 재현율 확보를 위해 단어 + 2-그램 보강 방식(`_tokenize`)을 유지한다.

## 청킹 기준

- 일반 텍스트: **청크 400자, overlap 60자** (`_CHUNK_SIZE`/`_CHUNK_OVERLAP` 상수 — 변경 시 상수만 수정, 숫자를 코드 곳곳에 흩뿌리지 말 것).
- 표/구조화 문서: 행·섹션 단위로 자른다 (글자 수로 뭉개지 말 것).
- 이미지 메타: 이미지 설명 + 위치 + 라벨을 하나의 도큐먼트로 합쳐 인덱싱.
- 청크에는 항상 출처(문서명·페이지/섹션)를 메타로 붙이고, 답변에는 `[doc1]` 식 인용 마크 필수 — 인용 없는 답변은 환각으로 간주.

## data.go.kr 응답 캐싱

- 공공데이터포털 API 응답은 **반드시 로컬 캐시를 거친다** (`backend/storage/pubdata.db` — `backend/pubdata/store.py`). 같은 질의로 API를 반복 호출하지 말 것: 일일 트래픽 제한(개발계정 기본 1,000회/일)이 있다.
- 캐시에는 수집 시각·출처 URL·공공누리 유형을 함께 저장한다.
- API 키는 `DATA_GO_KR_KEY` 환경변수만 사용 (Decoded 키 권장). 키/엔드포인트 하드코딩 금지.
- 새 공공데이터 소스는 `backend/pubdata/adapters.py` + `registry.py` 패턴으로 추가한다 — 개별 서비스 코드에서 requests를 직접 때리지 말 것.

## 인덱스 수명

- 인덱스는 코퍼스가 바뀔 때만 재빌드, 청크 임베딩은 캐시 (기존 동작 유지).
- 웹 검색으로 가져온 자료를 코퍼스에 추가하는 기능은 "추가 → 재인덱싱 → 즉시 검색 가능" 흐름을 보장할 것.

## 평가

- 검색 품질 변경(토크나이저·청킹·융합 가중치)은 `prototypes/rag-search/`의 샘플 문서로 최소 3개 질의의 before/after를 확인하고 나서 백엔드에 반영한다.
