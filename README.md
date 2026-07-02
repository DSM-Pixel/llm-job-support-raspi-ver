# llm-job-support

지엔소프트(주) × 유클리드소프트 「프로젝트형 청년 일경험」 멀티모달 AI 프로젝트 워크스페이스.

VLM · SAM · YOLOe · LLM · Hybrid RAG · AI Agent를 결합해
**자연어 질의 → 이미지 이해/검색/요약/보고서 생성** 서비스의
기획안과 기능별 프로토타입을 8주 동안 만들어냅니다.

> 자세한 컨텍스트와 컨벤션은 [CLAUDE.md](./CLAUDE.md)를 보세요.

## 빠른 시작

```bash
# 1) 가상환경 + 의존성
uv sync --extra dev --extra demo

# 2) 환경변수
cp .env.example .env
# .env 에 ANTHROPIC_API_KEY, DATA_GO_KR_KEY 등을 채우기

# 3) Claude Code 띄우기
claude
```

세션이 시작되면 `SessionStart` 훅이 현재 브랜치/팀/프로토타입 현황을 알려줍니다.

## 통합 웹 플랫폼 실행

프로토타입(라벨링·RAG·질의·보고서)을 한 화면에 묶은 FastAPI 서버입니다.

```bash
uv sync --extra web
./run_web.sh        # macOS/Linux/Git Bash  (PORT=9000 ./run_web.sh 로 포트 변경)
./run_web.ps1       # Windows PowerShell
```

→ http://127.0.0.1:8000  (API·구조는 [backend/README.md](./backend/README.md) 참고)

## 자주 쓰는 Claude Code 명령

| 명령 | 용도 |
|------|------|
| `/team-init <팀명>` | 새 팀 워크스페이스 생성 |
| `/prototype-scaffold` | Gradio/FastAPI 데모 1파일 생성 |
| `/planning-report` | 기획 보고서/기능 정의서/발표자료 초안 |
| `/run` | 만든 앱을 띄워 동작 확인 |

> 통합 서버를 빠르게 띄우려면 루트의 `run_web.sh` / `run_web.ps1` 사용.

## 자주 호출하는 subagent

| 에이전트 | 용도 |
|----------|------|
| `vlm-researcher` | Qwen2-VL/SAM/YOLOe 등 모델 후보 비교 |
| `rag-architect` | Hybrid RAG 파이프라인 설계 |
| `prototype-builder` | Gradio/FastAPI 데모 1파일 코드 |
| `public-data-finder` | data.go.kr 데이터셋/API 연계 |
| `planning-writer` | 한국어 기획서/발표자료 작성 |

## 디렉터리

```
.
├── CLAUDE.md           # 프로젝트 컨텍스트 (반드시 먼저 읽기)
├── pyproject.toml      # uv 기반
├── .claude/            # 하네스: settings/agents/skills/hooks
├── backend/            # 통합 FastAPI 서버 (web/ 서빙 + /api/*)
├── web/                # 통합 웹 UI (대시보드/라벨링/질의/RAG/보고서)
├── docs/               # 기획 보고서, 설계안, 발표자료, 작업노트
├── prototypes/         # 기능별 데모 (Gradio 원형)
├── teams/              # 팀별 작업 공간
└── data/               # 샘플 데이터 (대용량 제외)
```

## 라이선스

이 프로젝트는 **GNU Affero General Public License v3.0 이상(AGPL-3.0-or-later)** 으로 배포됩니다.
전문은 [`LICENSE`](./LICENSE) 파일을 참고하세요.

- 소스 코드를 자유롭게 사용·수정·재배포할 수 있으며, **네트워크(웹) 서비스로 제공하는 경우에도**
  이용자에게 대응하는 소스 코드를 공개해야 합니다.
- 객체 탐지에 사용하는 `ultralytics`(YOLO)가 AGPL-3.0이므로, 본 프로젝트도 이에 맞춰 AGPL-3.0으로
  통일하여 라이선스 충돌이 없도록 했습니다.
