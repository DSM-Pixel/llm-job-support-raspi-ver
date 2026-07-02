# 규칙: 테스트 (testing)

> 적용 대상: `tests/**`, `test_*.py`, `*_test.py` 를 만들거나 수정할 때.

## 기본

- 프레임워크는 **pytest 단일** (unittest 스타일 클래스 금지). 설정은 `pyproject.toml`의 `[tool.pytest.ini_options]`를 따른다 (`testpaths = ["tests"]`).
- 테스트 파일은 `tests/test_<대상모듈>.py`. 프로토타입 내부의 `test_*.py`(예: `prototypes/image-understanding/`)는 데모 검증 스크립트이므로 그 자리에 둔다 — pytest 수집 대상 아님.
- 실행: `uv run pytest` 또는 `pytest -q`. 커밋 전 통과 확인.

## 외부 API는 반드시 mock

- **Gemini / data.go.kr / 그 외 네트워크 호출을 실제로 때리는 테스트 금지.** `monkeypatch` 또는 `unittest.mock.patch`로 어댑터 함수(예: `services._gemini_generate`) 경계를 막는다.
- FastAPI 라우트는 `fastapi.testclient.TestClient`로 테스트하고, 서비스 계층은 MOCK 폴백 경로가 있으므로 그 경로를 활용한다.
- 네트워크가 정말 필요한 검증은 `@pytest.mark.integration` 마커로 분리하고 기본 실행에서 제외한다.

## .env 없이도 돌아가야 한다

- 테스트는 **API 키가 하나도 없는 CI/새 팀원 PC에서 그대로 통과**해야 한다.
- `os.environ["..."]` 직접 접근 코드를 테스트하려면 `monkeypatch.setenv("GEMINI_API_KEY", "test-key")`로 가짜 키를 주입한다.
- 키가 없을 때의 **폴백 경로(MOCK/어휘 임베딩)도 테스트 대상**이다 — "키 없음 → 200 + backend=MOCK" 같은 케이스를 꼭 넣는다.
- 테스트가 실제 `.env`를 읽지 않도록 주의 (`load_dotenv` 호출을 테스트에서 트리거하지 말 것).

## 기타

- 테스트가 파일을 쓰면 `tmp_path` fixture 사용. `backend/storage/`의 실제 DB를 건드리지 말 것.
- 느린 테스트(>2초)는 만들지 않는다. RPi5에서도 전체 스위트가 수십 초 안에 끝나야 한다.
- 한글 데이터(문서, 질의) 케이스를 최소 1개 포함 — 토크나이저/청킹이 한국어 전제이므로.
