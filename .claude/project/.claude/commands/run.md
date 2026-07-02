---
description: 현재 작업 중인 앱(통합 웹 서버 또는 프로토타입)을 실행해서 동작 확인
allowed-tools: Bash, Read, Glob
---

현재 작업 중인 앱을 띄워서 실제로 동작하는지 확인해라. 인자: `$ARGUMENTS` (비어 있으면 대화 맥락으로 판단)

## 무엇을 띄울지 결정

1. 인자로 프로토타입 이름이 오면 (예: `/run rag-search`) → `prototypes/<이름>/app.py`
2. 인자가 없으면: 최근 수정 파일이 `backend/`·`web/`이면 **통합 서버**, `prototypes/<x>/`면 해당 프로토타입.
3. 애매하면 통합 서버가 기본.

## 통합 서버 (backend + web)

```bash
./run_web.sh            # .venv 필요 — 없으면 먼저: uv sync --extra web
# 또는 직접: uv run uvicorn backend.app:app --reload --port 8000
```

- 백그라운드로 실행하고, 뜨면 `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/` 으로 200 확인.
- 작업 중이던 API가 있으면 해당 `/api/...` 엔드포인트도 curl로 1회 호출해 응답 JSON을 보여준다.
- 접속 주소(http://localhost:8000)와 관련 페이지(`/pages/rag.html` 등)를 사용자에게 알린다.

## 프로토타입 (Gradio)

```bash
uv run python prototypes/<feature>/app.py
```

- 백그라운드 실행 후 출력에서 로컬 URL을 찾아 사용자에게 알린다. 포트는 자동 할당이므로 출력 기준.

## 규칙

- 서버가 이미 떠 있으면 (포트 사용 중) 죽이지 말고 사용자에게 알리고 그 서버로 확인한다.
- 에러로 안 뜨면 로그를 그대로 보여주고 원인(의존성 미설치 / .env 없음 / import 에러)을 진단한다. `.env` 내용은 절대 출력하지 말 것.
- RPi5 기준이므로 기동이 느릴 수 있다 — 최대 30초 기다린 후 판단.
- 확인이 끝나도 사용자가 보고 있을 수 있으니 서버를 임의로 종료하지 않는다 (종료 여부를 묻는다).
