# api-test — Claude API 연동 테스트

본격적인 기능을 붙이기 전에 **Claude API가 실제로 호출되는지** 가장 먼저 확인하는 최소 프로토타입.

## 1. API 키 준비

1. https://console.anthropic.com 에서 API 키 발급
2. 템플릿을 복사해 `.env` 생성 후 키 입력:

   ```bash
   cp prototypes/api-test/.env.example prototypes/api-test/.env
   # .env 를 열어 ANTHROPIC_API_KEY 값을 채운다
   ```

   > `.env` 는 `.gitignore` 에 등록돼 있어 커밋되지 않습니다. 키는 절대 코드에 직접 쓰지 마세요.

## 2. 연결 스모크 테스트 (UI 없이)

터미널에서 응답 한 줄을 받아 연동을 검증:

```bash
uv run python prototypes/api-test/check_api.py
```

성공하면 응답 문장, 토큰 사용량, 요청 ID가 출력됩니다. 실패하면 원인(키 오류/모델 오류/네트워크 등)을 한국어로 안내합니다.

## 3. Gradio 채팅 데모

브라우저에서 Claude와 대화해보며 연동을 확인:

```bash
uv run --extra demo python prototypes/api-test/app.py
```

실행 후 출력되는 `http://127.0.0.1:7860` 주소를 열면 됩니다.

## 파일 구성

| 파일 | 설명 |
|------|------|
| `check_api.py` | UI 없는 연동 스모크 테스트 (가장 먼저 돌려볼 것) |
| `app.py` | 최소 Gradio 채팅 데모 (스트리밍 응답) |
| `.env.example` | 환경변수 템플릿 |

## 모델

기본값은 `claude-opus-4-8`. `.env` 에 `CLAUDE_MODEL` 을 지정하면 바꿀 수 있습니다
(예: 빠르고 저렴한 테스트는 `claude-haiku-4-5`).

## 다음 단계

연동이 확인되면 이 폴더를 베이스로 팀별 기능(이미지 업로드, 공공데이터 호출, RAG 검색 등)을
`prototypes/<feature>/` 아래에 새로 만들어 붙여나가면 됩니다.
