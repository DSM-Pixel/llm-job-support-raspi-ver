# llm-job-support

지엔소프트(주) × ㈜유클리드소프트 「프로젝트형 청년 일경험」 멀티모달 AI 프로젝트 — **DSM-Pixel 팀** 워크스페이스.
VLM·SAM·YOLOe·LLM·Fine-tuning·Hybrid RAG·AI Agent를 결합해 **자연어 질의 → 이미지 이해/공공데이터 검색/질의응답/요약/보고서 생성/업무 자동화**를 수행하는
**통합 멀티모달 AI 업무지원 플랫폼**의 기획안 + 기능별 프로토타입을 만든다.

> 본 CLAUDE.md는 모든 세션에서 자동 로드되는 프로젝트 컨텍스트다.
> 하네스(서브에이전트/스킬/훅) 재구축이 필요하면 `AI-hanes-explain.md`를 읽어라.

---

## 핵심 일정 (2026)

- 수행기간: **2026-06-04 ~ 2026-07-29 (8주)** — 코칭 2회(개요 공유 / 결과물·발표 피드백)
- 최종 산출물: 기획 보고서 + 기능 정의서 + UI/UX 설계안 + AI 서비스 아키텍처 + 데이터 구조 설계안 + 기능별 프로토타입 + 발표자료

## 팀 구성과 역할

| 팀원 | 담당 |
|------|------|
| 김근영 | 백엔드 / 파인튜닝 |
| 하채은 | RAG (공공데이터) |
| 이다연 | 디자인 |
| 염세현 | 프론트 |

전원 Claude Code 기반 **바이브 코딩**으로 작업한다. (구독: Fable 5로 구현 → 토큰 부족 시 Codex CLI로 보충)

## 현재 구현 상태 (main 기준)

작업 전에 반드시 이 현황을 인지하고, 이미 있는 코드를 재활용/확장할 것. 없는 걸 새로 만들기 전에 `backend/`, `web/`, `prototypes/` 먼저 확인.

- **`backend/`** — 백엔드 서버. **AI 모델들은 현재 외부 API 연동 방식으로 구성되어 있음** (로컬 추론 아님). 자연어/이미지 입력 종류에 따라 모델을 분기하는 구조가 목표.
- **`web/`** — 프론트엔드. **디자인은 현재 HTML(+CSS/JS) 정적 산출물 단계**. 백엔드 API와의 연동 및 내부 로직 채우기가 진행 중인 과제.
- **`prototypes/`** — 기능별 데모 (Gradio/FastAPI 1파일 원칙).
- **`docs/`** — 기획 보고서, 설계안, 발표자료.
- **`.claude/`** — Claude Code 하네스 완비: settings.json(권한/hook/env), 서브에이전트 5종, 스킬 3종, 훅 2종(ruff 자동 포맷, 세션 시작 컨텍스트), memory MCP 서버.

### 지금 우선순위 (멘토링 액션아이템)

1. **공공데이터 RAG 파트 개발** (하채은)
   - 문서 선택 + 자연어 질의응답 기능
   - 웹에서 문서 검색 후 코퍼스에 자료 추가하는 기능
   - 결과물은 이 리포(GitHub)에 반영
2. **웹 서버 오픈** — RPi5(8GB)에 백엔드를 올려 어디까지 감당 가능한지 검증
3. **디자인(HTML) → `web/` 프론트 통합** — 디자인 산출물을 받아 내부 로직/API 연동을 채워 넣기 (염세현·이다연)

## 인프라·API 제약 (중요 — 코드 작성 시 반드시 반영)

- **GPU 서버 없음.** 배포 대상은 **Raspberry Pi 5 (8GB)** 웹 서버. 무거운 로컬 추론을 전제로 코드를 짜지 말 것.
- **AI는 API 콜 우선.** 현재 사용 가능한 API 키는 **Gemini API뿐**이다. GPT/Claude API 키는 추후 지급 예정.
  - 따라서 런타임 LLM 호출 코드는 **provider를 쉽게 교체할 수 있게** 작성 (모델명/엔드포인트 하드코딩 금지, `.env` + 얇은 어댑터 계층).
  - `ANTHROPIC_API_KEY`가 `.env.example`에 있지만 **아직 키가 없으므로** Claude API 호출은 mock 또는 Gemini fallback으로 동작해야 함.
- **입력 분기**: 자연어 vs 사진(이미지) 처리에 따라 호출 모델을 분기. 대용량 일괄 처리는 (서버 확보 시) 로컬 LLM에서 전처리하는 방향 — 후보: Qwen, Kimi, Llama 계열. 교내망 서버를 얻으면 tailscale로 연동.
- **공공데이터 API**: data.go.kr 등 한국 공공 API는 https://github.com/yybmion/public-apis-4Kr 를 참고해 wrapping해서 사용. 키는 `DATA_GO_KR_KEY` (`.env`).

## 기술 스택

- **언어**: Python (백엔드/AI). 프론트는 `web/`의 HTML/CSS/JS.
- **패키지**: `uv` (`uv sync --extra dev --extra demo`). pip도 동작.
- **포맷/린트**: `ruff` 단일 (black/flake8 추가 금지 — PostToolUse hook이 자동 포맷).
- **테스트**: `pytest` (필요 시).
- **UI**: 데모는 Gradio 1순위, 서비스 본체는 FastAPI + `web/` 프론트.
- **RAG**: BM25 + dense 하이브리드 (ChromaDB/FAISS + rank-bm25), 한국어 임베딩(BGE-m3 계열), 리랭커 1단계. 프레임워크는 LangChain/LlamaIndex를 얇게.
- **Vision**: VLM(Qwen2.5-VL 계열), SAM/SAM2, YOLOe — 단, RPi5 제약상 우선 API/캡션 기반으로, 로컬 비전 추론은 서버 확보 후.

## 디렉터리 레이아웃

```
llm-job-support/
├── CLAUDE.md              # ← 이 파일 (자동 로드)
├── AI-hanes-explain.md    # 하네스 재구축 가이드
├── pyproject.toml         # uv 기반
├── .env.example           # ANTHROPIC_API_KEY, DATA_GO_KR_KEY 등
├── .mcp.json              # memory MCP 등록
├── .claude/               # settings / agents / skills / hooks / mcp
├── backend/               # 서버 (AI는 API 연동 구조)
├── web/                   # 프론트 (디자인 HTML 기반, 로직 연동 중)
├── prototypes/<feature>/  # 기능별 데모
├── docs/                  # 기획서·설계안·발표자료
└── data/                  # 샘플 데이터 (대용량 ignore)
```

## Claude Code 활용

- `/run` — 만든 앱을 띄워 동작 확인
- `/prototype-scaffold` — Gradio/FastAPI 데모 1파일 생성
- `/planning-report` — 기획 보고서/기능 정의서/발표자료 초안
- `/team-init <팀명>` — 팀 워크스페이스 생성
- 서브에이전트: `vlm-researcher`(모델 비교), `rag-architect`(RAG 설계), `prototype-builder`(데모 코드), `public-data-finder`(data.go.kr 연계), `planning-writer`(한국어 기획서)

## 장기 기억 (memory MCP)

세션 간 진행상황·결정사항 유지용. (`.claude/mcp/memory_server.py`, SQLite `.claude/memory.db`, 커밋 금지)

- 세션 시작/맥락 필요 시: `memory_search`로 먼저 검색 (예: "RAG 파트 어디까지 했지")
- 중요한 결정·진행상황 발생 시: `memory_save(content, tags)` 즉시 저장. 한 건 = 한 사실.
- 팀 공유가 필요한 합의는 memory가 아니라 이 CLAUDE.md 또는 `docs/`에 기록.
- 주의: `.mcp.json`의 경로가 특정 로컬 PC 기준 절대경로다. 다른 환경이면 자기 경로로 수정(커밋은 상대경로 형태 권장).

## 바이브 코딩 원칙

- **시연 가능한 최소 결과물** 먼저 → 반복 개선. 추상화는 같은 패턴 3회 반복 후.
- 데모 시나리오 우선: "포트홀 영역을 찾아줘", "공공데이터포털 기반으로 관련 통계를 보여줘", "검색 결과를 요약해서 보고서로 만들어줘", "업무 절차를 자동으로 추천해줘" — 이 한 줄이 실제로 돌아가야 한다.
- MOCK 데이터로 흐름부터, 실제 API/모델은 나중에 연결.
- 무거운 파인튜닝/학습은 마지막에. 우선 사전학습 모델 + 프롬프트.

## 코딩 컨벤션

- 명시적 > 마법. 함수 우선, 클래스는 상태가 진짜 필요할 때만.
- 타입 힌트는 공개 함수에만. 한글 주석 OK, 함수/변수명은 영어.
- 에러는 사용자 친화적으로 (`gr.Error("이미지를 먼저 업로드해주세요")`).
- **시크릿은 `.env`만** — 하드코딩·커밋 절대 금지.
- 노트북은 실험용, 시연 산출물은 `.py` 또는 Gradio 앱으로.

## 협업 / 깃 정책

- **main 직접 commit 금지.** 작업 브랜치(`<이름>/<topic>` 또는 `team-<n>/<topic>`) → PR.
- 커밋 메시지 한국어 OK, 동사로 시작: `공공데이터 RAG 질의응답 추가`.
- 모델 weight·데이터셋 원본·`.env`·`memory.db` 커밋 금지.
- Claude가 임의로 git commit 하지 않는다 — 사용자가 요청할 때만.

## 무엇을 하지 말 것

- RPi5에서 못 돌아갈 무거운 로컬 추론을 기본 경로로 설계하지 말 것.
- 아직 키가 없는 Claude/GPT API를 필수 의존으로 박지 말 것 (Gemini 우선 + 어댑터).
- `backend/`·`web/`에 이미 있는 구현을 무시하고 처음부터 다시 만들지 말 것.
- 공공데이터포털 이용약관·라이선스(공공누리 유형) 무시 금지.
- 개인정보(차량 번호판, 얼굴 등) 포함 데이터는 마스킹 후 사용.
- ruff format 실패 코드 커밋 금지 (hook이 잡음).

## 참고

- GitHub Org/Repo: https://github.com/DSM-Pixel/llm-job-support
- 참여기업: 지엔소프트(주) — 대전 유성구 문지로 272-16 AI인공지능센터
- 운영기관: ㈜유클리드소프트 / 사전직무교육: 2026-05-29~30, 대전지식산업센터 206호
