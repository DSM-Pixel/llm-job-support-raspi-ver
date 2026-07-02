# 규칙: backend/ API 설계 (api-design)

> 적용 대상: `backend/**/*.py` 를 읽거나 수정할 때 항상 준수.

## FastAPI 컨벤션

- 진입점은 `backend/app.py` 하나. 새 라우트는 `/api/<도메인>/<동작>` 형태로 여기에 추가한다.
- 요청/응답 스키마는 Pydantic `BaseModel`로 고정한다. 프론트(`web/assets/js/*.js`)가 이 계약에 의존하므로 **기존 응답 필드를 임의로 삭제·개명하지 말 것** (추가는 OK).
- 비즈니스 로직은 라우트 함수에 넣지 말고 `backend/services.py`(또는 도메인 모듈 `backend/pubdata/` 식)로 분리한다. 라우트는 얇게.
- MOCK 응답에는 반드시 `"backend": "MOCK"` 필드를 유지한다 — 프론트가 가짜 데이터임을 표시하는 데 쓴다.
- 에러는 `HTTPException(status_code, detail="한국어 사용자 메시지")`. 스택트레이스를 응답에 노출하지 말 것.

## LLM provider 어댑터 계층 (강제)

- **LLM 호출 코드는 절대 라우트/서비스 본문에 SDK를 직접 박지 않는다.** 반드시 얇은 어댑터 함수를 거친다 (`services.py`의 `_gemini_generate` 패턴처럼: 타임아웃·사용량 추적·폴백을 어댑터가 담당).
- 현재 키는 **Gemini뿐**이다. Claude/GPT 키는 추후 지급 → 새 provider는 어댑터에 분기만 추가하면 되도록 작성한다. 특정 provider SDK 타입이 어댑터 밖으로 새어나가면 안 된다.
- **모델명·엔드포인트·API 키 하드코딩 금지.** 모델명은 모듈 상단 상수 또는 `.env`(`GEMINI_MODEL` 등), 키는 항상 `os.environ` / `python-dotenv`.
- 키가 없거나 429(rate limit)면 **MOCK/어휘 폴백으로 항상 동작**해야 한다. "키 없으면 크래시"는 리뷰에서 반려.
- `ANTHROPIC_API_KEY`는 `.env.example`에 있지만 아직 키가 없다 — Claude 호출 경로는 mock 또는 Gemini fallback 필수.

## RPi5 제약 (배포 대상: Raspberry Pi 5, 8GB RAM, GPU 없음)

- **무거운 로컬 추론을 기본 경로로 넣지 말 것.** torch/transformers/ultralytics 계열 import는 lazy(함수 내부)로, 미설치 시 MOCK 폴백.
- 새 의존성 추가 전 질문: "RPi5에서 pip 설치·구동이 되는가?" 안 되면 optional-dependencies(`[vision]`, `[seg]`)로 격리하고 코드에는 폴백을 둔다.
- 상시 메모리 점유가 큰 전역 객체(모델, 대형 인덱스) 금지. lazy load + 필요 시 해제.
- 대용량 일괄 처리는 (교내망 서버 확보 시) 별도 워커로 뺀다 — RPi5 웹 서버 프로세스 안에서 돌리지 않는다.

## 상태/저장

- 런타임 상태 파일·DB는 `backend/storage/` 또는 `backend/.gemini_state.json`처럼 gitignore 처리된 위치에만 쓴다.
- 사용자 개인정보(`users.db`)를 로그로 출력하지 말 것.

## 라이선스

- 이 리포는 **AGPL-3.0** (오픈소스 대회 출품용). `pyproject.toml`의 `license` 및 `LICENSE` 파일을 **절대 다른 라이선스로 바꾸지 말 것.** AGPL과 호환 안 되는 라이선스의 코드/모델을 들여오지도 말 것.
