# AI 하네스 재구축 가이드 (AI-hanes-explain)

> **목적**: 이 문서 하나만 주면 어떤 AI 에이전트(Claude Code, Codex, Cursor 등)도
> `llm-job-support` 프로젝트의 Claude Code 하네스를 **똑같이 재구축**할 수 있게 한다.
>
> 읽는 대상은 **AI 에이전트**다. 사람이 읽어도 되지만, 에이전트가 단계별로
> 그대로 따라할 수 있도록 명령·파일 경로·내용을 모두 명시한다.

---

## 0. 한 줄 요약

> 한국 지엔소프트(주) × 유클리드소프트의 8주 멀티모달 AI 일경험 프로젝트(5팀×4명)를 위한
> Claude Code 하네스. Python(uv) + Gradio + VLM/SAM/RAG/Agent + 한국어 기획서 산출물에 특화.

---

## 1. 사전에 수집해야 하는 정보

이 하네스를 다른 프로젝트에 적용할 경우, **반드시 먼저 사용자에게 물어야 하는 4가지**:

| 질문 | 이 프로젝트의 답 |
|------|------------------|
| 프로젝트 성격 (LLM 앱 / Claude Code 에이전트 / 일반 풀스택 / 미정) | LLM/멀티모달 AI 서비스 (Python 기반) |
| 하네스 범위 (CLAUDE.md / settings.json / subagent / skill / hook / MCP) | CLAUDE.md, settings.json, subagent, skill, hook 전부 |
| 기술 스택 (Python / TS / 혼합 / 미정) | Python |
| 도메인 컨텍스트 (산업, 일정, 팀 구성, 산출물 형태) | 지엔소프트 멀티모달 AI, 8주, 5팀×4명, 기획서+프로토타입 |

다른 프로젝트라면 위 4가지를 답하게 한 뒤 아래 템플릿의 한국어 문구·예시·도메인 부분만 교체.

---

## 2. 폴더 청사진

다음 구조를 **루트 기준**으로 만든다. (모든 경로는 프로젝트 루트 기준 상대 경로)

```
.
├── AI-hanes-explain.md          # ← 이 문서
├── CLAUDE.md                    # 프로젝트 컨텍스트 (자동 로드)
├── README.md                    # 빠른 시작 가이드
├── pyproject.toml               # uv 기반 Python 프로젝트
├── .gitignore                   # Python + Claude artifacts
├── .env.example                 # 환경변수 템플릿
└── .claude/
    ├── settings.json            # 권한 + hook + env
    ├── agents/
    │   ├── vlm-researcher.md
    │   ├── rag-architect.md
    │   ├── prototype-builder.md
    │   ├── public-data-finder.md
    │   └── planning-writer.md
    ├── skills/
    │   ├── team-init/SKILL.md
    │   ├── prototype-scaffold/SKILL.md
    │   └── planning-report/SKILL.md
    └── hooks/
        ├── format_py.py         # PostToolUse: ruff format/check
        └── session_start.py     # SessionStart: 현재 상태 컨텍스트
```

**총 14개 파일.** 이 중 `.claude/settings.local.json`은 Claude Code가 자동 생성하므로 만들지 않는다.

---

## 3. 구축 순서 (그대로 따라할 것)

1. **Step 1 – 프로젝트 메타** : `CLAUDE.md`, `README.md`, `pyproject.toml`, `.gitignore`, `.env.example`
2. **Step 2 – 하네스 권한/환경** : `.claude/settings.json`
3. **Step 3 – 훅 스크립트** : `.claude/hooks/format_py.py`, `.claude/hooks/session_start.py`
4. **Step 4 – Subagents 5개** : `.claude/agents/*.md`
5. **Step 5 – Skills 3개** : `.claude/skills/*/SKILL.md`
6. **Step 6 – 검증** : JSON 파싱, 훅 dry-run

각 단계 사이에 git commit을 강요하지 말 것. 사용자가 명시적으로 요청할 때만 커밋.

---

## 4. 각 파일의 전체 내용

### 4.1 `CLAUDE.md`

```markdown
# llm-job-support

지엔소프트(주) × 유클리드소프트 「프로젝트형 청년 일경험」 멀티모달 AI 프로젝트 워크스페이스.
참여 청년이 **Claude Code 바이브 코딩** 방식으로 멀티모달 Vision AI / 생성형 AI 서비스의
**기획안 + 기능별 프로토타입**을 만들어내는 것이 최종 목표입니다.

> 본 CLAUDE.md는 모든 세션에서 자동으로 로드되는 프로젝트 컨텍스트입니다.
> 팀별 세부 컨텍스트는 `teams/<team-name>/CLAUDE.md`에 따로 둡니다(있을 경우).

---

## 프로젝트 한 줄 요약
VLM·SAM·YOLOe·LLM·Fine-tuning·Hybrid RAG·AI Agent 기술을 결합해
**자연어 질의 → 이미지 이해/검색/요약/보고서 생성/업무 자동화**를
수행하는 AI 서비스 후보 모델을 발굴·검증한다.

## 핵심 일정 (2026년)
- 수행기간: **2026-06-04 ~ 2026-07-29 (8주)**
- 코칭 2회 (개요/결과 피드백)
- 최종 산출물: 기획 보고서 + 기능별 프로토타입 + 발표자료

## 팀 구성
- 5팀 × 4명 = 20명
- 세부 과제 예: 도로 파손 라벨링 자동화, CCTV 이상행동 검색·분석, 시설물 점검 데이터,
  공공데이터포털 연계 QA, 하이브리드 RAG 지식검색, 요약/보고서 자동화

## 기술 스택
- **언어**: Python. UI는 Gradio 1순위, 복잡하면 FastAPI/Streamlit.
- **패키지 매니저**: `uv` (재현성). pip도 동작.
- **포맷/린트**: `ruff` 통합 (black/flake8 추가 금지).
- **테스트**: `pytest`.
- **모델 후보**: Qwen2.5-VL/LLaVA/InternVL, SAM/SAM2/YOLOe, Claude API, vLLM/Ollama,
  LangChain/LlamaIndex + ChromaDB/FAISS + BM25 하이브리드.

## 산출물 형태
- `docs/` — 기획 보고서, 기능 정의서, 아키텍처/데이터 설계안, 발표자료
- `prototypes/<feature>/` — 기능별 데모(Gradio 1파일 또는 작은 패키지)
- `teams/<team-name>/` — 팀별 작업 공간

## 바이브 코딩 원칙
- **시연 가능한 최소 결과물** 먼저, 그 위에서 개선
- Gradio `gr.Interface` 한 줄로 띄울 수 있으면 그렇게
- 추상화는 같은 패턴 3번 반복 후
- "포트홀 영역 찾아줘" 같은 한 줄 시나리오가 돌아가야 함
- MOCK 데이터로 흐름부터, 실 모델/API는 나중에
- 무거운 모델 학습은 마지막에

## 코딩 컨벤션
- **명시적 > 마법**: 매직 메서드, 메타클래스, 동적 import 자제
- **함수 우선**, 클래스는 상태가 진짜 필요할 때만
- **타입 힌트는 공개 함수에만**
- **에러는 사용자에게 의미 있게** (`gr.Error("이미지를 먼저 업로드해주세요")`)
- **시크릿은 `.env`** (코드 하드코딩 X, 커밋 X)
- **노트북은 실험용**, 발표/시연은 .py 또는 Gradio 앱으로
- **한글 주석 OK**. 단 함수/변수명은 영어

## 디렉터리 레이아웃
\```
llm-job-support/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .claude/
├── docs/
├── prototypes/<feature>/
├── teams/<team-name>/
├── data/
└── src/llm_job_support/
\```

## 협업 / 깃 정책
- main 직접 commit 금지. 팀별 `team-<n>/<topic>` 브랜치
- 커밋 메시지 한국어 OK, 동사로 시작
- 모델 weight, 데이터셋 원본은 커밋 금지 (`data/` 기본 ignore)
- 시크릿 절대 커밋 금지

## Claude Code 활용 가이드 (팀원에게)
1. 막막하면 `/run`
2. 기획서는 `/planning-report`
3. 새 팀 시작은 `/team-init <팀명>`
4. VLM/RAG/공공데이터는 전용 subagent
5. 모르는 라이브러리는 그냥 질문

## 무엇을 하지 말 것
- 처음부터 거대한 모놀리식 백엔드 설계 X
- 데이터 라이선스 무시 X (공공데이터포털 이용약관 확인)
- 개인정보(번호판/얼굴) 포함 데이터는 마스킹 후 사용
- ruff format 실패 코드 커밋 X (hook이 잡음)
```

> **다른 프로젝트에 적용 시**: "지엔소프트", 일정, 팀 구성, 도메인 예시(도로 파손/CCTV)만 교체.

### 4.2 `README.md`

- 한 줄 프로젝트 설명 + CLAUDE.md 링크
- `uv sync` / `.env` / `claude` 실행 가이드
- `/team-init`, `/prototype-scaffold`, `/planning-report`, `/run` 명령 표
- subagent 5종 용도 표
- 디렉터리 트리 요약

### 4.3 `pyproject.toml`

핵심 포인트:
- `requires-python = ">=3.11"`
- `dependencies`: anthropic, python-dotenv, requests, pillow (가볍게)
- `optional-dependencies`:
  - `dev`: ruff, pytest, ipython
  - `demo`: gradio, streamlit
  - `rag`: chromadb, rank-bm25, sentence-transformers
  - `vision`: 주석 처리 (torch/transformers/ultralytics — 필요 시 설치)
- `[tool.uv] package = false`
- `[tool.ruff]` line-length 100, target py311, extend-exclude `notebooks/data/weights/prototypes/*/sample`
- `[tool.ruff.lint]` select E/F/I/B/UP/SIM/RUF, ignore E501·B008
- `[tool.ruff.format]` double quotes, space indent
- `[tool.pytest.ini_options]` testpaths=tests, -q

### 4.4 `.gitignore`

다음 카테고리 모두 포함:
- Python(`__pycache__`, `.venv`, `*.egg-info`, ruff/mypy/pytest cache)
- Secrets(`.env`, `.env.*` 제외 `.env.example`, `*.key`, credentials*.json)
- Notebooks(`.ipynb_checkpoints`)
- Data/Models 대용량(`data/raw|interim|processed|external`, `weights/`, `*.pt|.pth|.safetensors|.onnx|.gguf`)
- ML artifacts(`runs/`, `wandb/`, `mlruns/`, `lightning_logs/`, `outputs/`)
- Gradio/Streamlit(`gradio_cached_examples/`, `flagged/`, `.streamlit/secrets.toml`)
- Editor/OS(`.idea/`, `.vscode/`, `*.swp`, `.DS_Store`, `Thumbs.db`)
- Claude project-local(`.claude/settings.local.json`, `.claude/.cache/`, `.claude/logs/`)

### 4.5 `.env.example`

```
ANTHROPIC_API_KEY=sk-ant-...
DATA_GO_KR_KEY=
KMA_API_KEY=
ITS_API_KEY=
HF_TOKEN=
```

각 키 위에 한 줄 주석으로 어떤 용도인지 + Decoded/Encoded 같은 주의사항.

### 4.6 `.claude/settings.json`

**스키마**: `https://json.schemastore.org/claude-code-settings.json`

**permissions.allow** (대표 패턴):
- `Bash(uv:*)`, `Bash(uv run:*)`, `Bash(uvx:*)`, `Bash(pip:*)`, `Bash(pip install:*)`,
  `Bash(python:*)`, `Bash(python3:*)`, `Bash(python -m:*)`,
  `Bash(pytest:*)`, `Bash(ruff:*)`, `Bash(ruff format:*)`, `Bash(ruff check:*)`, `Bash(mypy:*)`,
  `Bash(gradio:*)`, `Bash(streamlit run:*)`, `Bash(uvicorn:*)`
- `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git show:*)`,
  `Bash(git branch:*)`, `Bash(git add:*)`, `Bash(git restore:*)`, `Bash(git stash:*)`,
  `Bash(git switch:*)`, `Bash(git checkout:*)`
- `Bash(ls:*)`, `Bash(mkdir:*)`, `Bash(tree:*)`, `Bash(file:*)`
- PowerShell 변형: `PowerShell(uv:*)`, `PowerShell(uvx:*)`, `PowerShell(python:*)`,
  `PowerShell(pytest:*)`, `PowerShell(ruff:*)`, `PowerShell(Get-ChildItem:*)`,
  `PowerShell(Test-Path:*)`, `PowerShell(New-Item:*)`
- `WebFetch(domain:...)`: `docs.anthropic.com`, `huggingface.co`, `github.com`,
  `raw.githubusercontent.com`, `data.go.kr`, `www.data.go.kr`, `gradio.app`,
  `fastapi.tiangolo.com`, `python.langchain.com`, `docs.llamaindex.ai`

**permissions.deny**:
- `Bash(git push --force*)`, `Bash(git reset --hard*)`, `Bash(rm -rf /*)`, `Bash(rm -rf ~*)`
- `PowerShell(Remove-Item -Recurse -Force C:*)`
- `Read(.env)`, `Read(.env.*)`, `Read(**/credentials.json)`, `Read(**/service-account*.json)`

**env**:
- `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1` (Windows 한글 깨짐 방지)

**hooks**:
- `PostToolUse` 매처 `Edit|Write|MultiEdit` → `python .claude/hooks/format_py.py`
- `SessionStart` (매처 없음) → `python .claude/hooks/session_start.py`

### 4.7 `.claude/hooks/format_py.py`

핵심 로직:
1. `json.load(sys.stdin)`으로 hook payload 받기
2. `tool_input.file_path` 추출
3. `.py` 확장자가 아니거나 파일이 없으면 exit 0
4. `shutil.which("ruff")` 없으면 exit 0 (조용히)
5. `subprocess.run([ruff, "format", path], timeout=15, check=False, capture_output=True)`
6. `subprocess.run([ruff, "check", "--fix", "--exit-zero", path], timeout=15, check=False, capture_output=True, text=True)`
7. 남은 경고만 `stderr`로 흘려 Claude가 확인 가능
8. 항상 exit 0 (사용자 흐름 차단 금지)

### 4.8 `.claude/hooks/session_start.py`

핵심 로직:
1. `git rev-parse --abbrev-ref HEAD`로 현재 브랜치
2. `git status --porcelain`로 미커밋 파일 개수
3. `teams/` 폴더 스캔하여 팀 목록
4. `prototypes/` 폴더 스캔하여 첫 6개 표시 (나머지는 …)
5. 출력 형식:
   ```json
   {
     "hookSpecificOutput": {
       "hookEventName": "SessionStart",
       "additionalContext": "## llm-job-support 세션 컨텍스트\n- 브랜치: ...\n- ..."
     }
   }
   ```
6. timeout 3s, 모든 git 호출은 `check=False`로 실패해도 통과
7. 출력은 `json.dumps(..., ensure_ascii=False)`로 한글 보존

### 4.9 Subagents (`.claude/agents/*.md`)

각 파일은 YAML frontmatter + 시스템 프롬프트.

공통 frontmatter 필드:
- `name`: 파일명과 동일한 kebab-case
- `description`: **언제 이 에이전트를 호출해야 하는지** (Claude가 자동 라우팅에 사용)
- `tools`: 허용 도구 화이트리스트 (생략하면 모든 도구)

#### `vlm-researcher.md`
- **description**: VLM/SAM/YOLOe 등 멀티모달 모델 선택·통합·파인튜닝 조사. 라벨링 자동화/객체 탐지·분할 시 모델 추천·비교.
- **tools**: Read, Glob, Grep, WebFetch, WebSearch, Bash
- **핵심 행동**:
  1. 추천에 항상 "왜": 라이선스/VRAM/속도/한국어 품질
  2. 로컬 가능 여부 먼저 확인, CPU/소형 GPU 대안 제시
  3. 공개 모델 우선
  4. 벤치마크보다 도메인 fit 우선
  5. 풀 파인튜닝 전에 zero-shot/few-shot/LoRA
- **산출**: 모델 비교표 / 추론 최소 스니펫 / 데이터 요구량 / 다음 단계 체크리스트
- **모델 카테고리**: VLM(Qwen2.5-VL/LLaVA/InternVL2/MiniCPM-V/Phi-3.5-V/Gemma3),
  분할(SAM/SAM2/Grounded-SAM/FastSAM/MobileSAM), 검출(YOLOe/YOLOv11/RT-DETR/Grounding-DINO),
  OCR(PaddleOCR/EasyOCR/Surya), 임베딩(SigLIP/CLIP/DINOv2)

#### `rag-architect.md`
- **description**: Hybrid RAG(BM25+dense), 문서·이미지·메타 통합 인덱싱, 청킹, 리랭킹, 평가 설계.
- **tools**: Read, Glob, Grep, WebFetch, WebSearch, Bash
- **핵심 원칙**:
  1. 가장 작은 RAG부터 (FAISS in-memory + BM25 + chunk 5)
  2. 하이브리드 디폴트 (한국어 → ko-bm25 필요)
  3. 청크: 문서 300-500토큰/50 overlap, 표는 행/섹션, 이미지는 메타+캡션 합치기
  4. 리랭킹 1단계 필수 (Cohere/BGE-reranker-v2-m3/Jina)
  5. 평가 필수 (RAGAS/골든셋/LLM judge)
  6. 출처 인용 마크 필수
- **추천 스택**: ChromaDB → Qdrant → Pinecone, 임베딩 BGE-m3/multilingual-e5/KURE-v1,
  리랭커 bge-reranker-v2-m3, framework LlamaIndex/LangChain(얇게), LLM Claude Sonnet 4.6 또는 Qwen2.5-7B
- **멀티모달**: 캡션 인덱싱 + CLIP/SigLIP 듀얼

#### `prototype-builder.md`
- **description**: Gradio/FastAPI/Streamlit 1파일 데모. "시연 가능한 최소 결과물" 작성.
- **tools**: Read, Write, Edit, Glob, Grep, Bash, WebFetch
- **규칙**:
  1. 첫 결과물 단일 파일 `prototypes/<feature>/app.py`
  2. Gradio 1순위 (이미지/오디오 input)
  3. MOCK 데이터로 흐름부터
  4. 모델 lazy load (함수 내부 첫 호출)
  5. `gr.Error(...)`로 친화적 에러
  6. 코드 상단 docstring에 시연 시나리오 한 줄
  7. 포트 자동, CPU 대체 지원
- **표준 골격**: Gradio Blocks + Image input/output + Textbox query + Button click
- **디렉터리**: `prototypes/<feature-kebab>/{app.py, README.md, requirements.txt, sample/}`

#### `public-data-finder.md`
- **description**: 공공데이터포털(data.go.kr) API/오픈데이터 탐색·연계 코드 생성.
- **tools**: Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Bash
- **동작**:
  1. WebFetch로 data.go.kr 직접 조회, 가짜 endpoint 만들지 말 것
  2. API 키 종류(Encoded/Decoded), 호출 제한 명시
  3. JSON vs XML 확인
  4. CSV 다운로드면 API 안 쓰고 pandas 추천
- **데이터셋 카테고리**: 도로/시설물(국토부), CCTV(ITS), 교통/사고(TAAS, 도로교통공단),
  기상(기상청 apihub), 행정/통계(KOSIS, 행안부 도로명주소)
- **표준 코드**: `requests.get(url, params={"serviceKey": os.environ["DATA_GO_KR_KEY"], ...})`
- **라이선스**: 공공누리 1-4 유형 확인, 개인정보 마스킹

#### `planning-writer.md`
- **description**: 한국어 기획 보고서/기능 정의서/아키텍처 설계안/발표자료 초안. 지엔소프트 양식 따름.
- **tools**: Read, Write, Edit, Glob, Grep
- **원칙**:
  1. 문어체("~합니다") 유지, 한자어 풀어쓰기
  2. 결론 맨 앞
  3. 구체적 숫자 ("8주", "5팀×4명", "후보 모델 3종")
  4. 마케팅 단어 금지 ("혁신적/최첨단/획기적")
  5. 시연 시나리오 1-2개 필수
- **섹션 구조**: 개요/배경/내용/기능정의/아키텍처/데이터·공공데이터/UI-UX/시연/일정/기대효과/위험
- **기능 정의서 표**: `| 기능명 | 입력 | 처리 | 출력 | 시연 시나리오 |`
- **아키텍처**: ASCII 또는 Mermaid
- **발표자료**: Marp 호환 .md, 슬라이드당 5줄 이내

### 4.10 Skills (`.claude/skills/<name>/SKILL.md`)

공통 frontmatter:
- `name`, `description`, `allowed-tools: [Bash, Read, Write, Edit, Glob, AskUserQuestion]`

#### `/team-init`
- **입력 수집** (AskUserQuestion): 팀명, 세부 과제(6지선다), 팀원 4명 닉네임
- **이미 존재하면 멈춤** (덮어쓰지 말 것)
- **생성**: `teams/<팀명>/{CLAUDE.md, README.md, notes/, prototype/, data/}`
- **CLAUDE.md 채우기**: 세부 과제, 팀원, 진행 현황 체크리스트(문제 정의→모델 선정→데이터→프로토타입→시연→기획서→발표), 시연 시나리오, 관련 디렉터리
- **마지막**: git status로 새 파일 보여주고 다음 행동 제안 (vlm-researcher / prototype-builder)
- **금지**: git commit, 팀별 가상환경, API 키 자동 채움

#### `/prototype-scaffold`
- **입력 수집**: 기능 이름(kebab-case), 프레임워크(Gradio default), 입력 유형, 출력 유형, 시연 시나리오 한 줄
- **생성**: `prototypes/<feature>/{app.py, README.md, requirements.txt, sample/}`
- **app.py 규칙**: docstring에 시연 시나리오, MOCK 함수, `# TODO(<feature>):` 마커, lazy load, gr.Error
- **표준 골격**: Gradio Blocks + Image + Textbox + Button
- **README**: 시연 시나리오 + `uv run python prototypes/<feature>/app.py` 실행 명령 + TODO 체크리스트
- **마지막 행동**: 파일 경로 출력 + 실행 명령 + "지금 띄워볼까요?" 확인
- **금지**: 초기 패키지화, 모델 weight import-time 다운로드, 시나리오 없는 진행

#### `/planning-report`
- **입력 수집**: 문서 종류(기획보고서/기능정의서/아키텍처/발표자료), 팀명(teams/ 스캔), 시연 시나리오 한 줄
- **생성 위치**: `docs/<팀명>-<문서종류>.md`, 발표자료는 `docs/slides/<팀명>.md`
- **충돌 시**: `-v2.md` suffix
- **템플릿**:
  - 기획 보고서: 11섹션 (개요/배경/내용/기능정의/아키텍처/데이터·공공데이터/UI/시연/일정/기대효과/위험)
  - 기능 정의서: 표 형식, 시연 시나리오 1줄 필수
  - 아키텍처: ASCII 다이어그램 + 컴포넌트 설명 + 데이터 흐름 + 외부 의존성
  - 발표자료: Marp frontmatter + `---` 슬라이드 구분, 슬라이드당 5줄 이내
- **작성 가이드**: 빈 섹션 금지(`<TODO: ...>` 마커), 표 5행 이하, 발표 슬라이드 5줄 이내

---

## 5. 검증

각 단계 후 다음 명령으로 검증.

```bash
# 1) settings.json JSON 파싱
python -c "import json; json.load(open('.claude/settings.json', encoding='utf-8'))"

# 2) format_py hook 무결성 (Python 아닌 파일로)
echo '{"tool_input":{"file_path":"pyproject.toml"}}' | python .claude/hooks/format_py.py
# → exit 0, stdout 비어있음

# 3) session_start hook 출력 형식
echo '{}' | python .claude/hooks/session_start.py
# → JSON 출력, hookSpecificOutput.additionalContext 포함

# 4) 폴더 구조
find .claude -type f | sort
# → agents 5개, skills 3개 SKILL.md, hooks 2개, settings.json
```

기대 결과:
- settings.json: 파싱 성공
- format_py.py: exit 0, 출력 없음
- session_start.py: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}`
- 파일 개수: 11개 (settings.local.json은 제외 — Claude가 자동 생성)

---

## 6. 확장 가이드

### MCP 추가
이 프로젝트는 기본 MCP를 깔지 않았다. 필요 시 후보:
- **Notion**: 기획서·회의록 공유 → `claude_ai_Notion__*`
- **Filesystem**: 외부 데이터 폴더 접근
- **GitHub**: 이슈/PR 자동화
- **공공데이터포털 커스텀 MCP**: 자주 쓰는 데이터셋이 있으면 직접 작성

`settings.json` 또는 `.mcp.json`에 등록.

### 새 Subagent 추가
1. `.claude/agents/<name>.md` 작성
2. frontmatter `name`/`description`/`tools`/(`model`) 필수
3. description은 **언제 호출할지** 명확히 (자동 라우팅 기준)
4. 시스템 프롬프트는 "원칙 → 산출 형식 → 금지 사항" 순서가 잘 먹힘

### 새 Skill 추가
1. `.claude/skills/<name>/SKILL.md` 작성
2. frontmatter `name`/`description`/`allowed-tools`
3. AskUserQuestion으로 입력 수집 → 표준 생성 → 마지막 안내
4. 슬래시 명령으로 호출됨 (`/<name>`)

### 새 Hook 추가
1. `.claude/hooks/<name>.py` 작성, stdin JSON 읽기 → 항상 exit 0
2. `.claude/settings.json` `hooks.<EventName>`에 등록
3. 이벤트: PreToolUse, PostToolUse, SessionStart, Stop, UserPromptSubmit 등
4. matcher는 정규식 (예: `"Edit|Write|MultiEdit"`)

---

## 7. 자주 묻는 질문

**Q. Windows에서 PowerShell 외에 bash도 쓰나?**
A. Bash와 PowerShell 권한을 둘 다 허용해뒀다. Claude Code가 선택한 셸에 맞춰 실행.

**Q. 훅이 ruff 미설치 환경에서 실패하지 않는가?**
A. `shutil.which("ruff")`로 사전 체크 후 없으면 exit 0. 학생 PC 환경 다양성 대비.

**Q. 한글 깨짐 방지는?**
A. `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` env로 강제. `json.dumps(..., ensure_ascii=False)` 사용.

**Q. data/, weights/는 왜 .gitignore?**
A. 데이터셋·모델 가중치는 GB 단위라 깃 저장소에 부적합. 별도 스토리지(HF Hub, 회사 NAS) 권장.

**Q. settings.local.json은?**
A. Claude Code가 자동 생성하는 로컬-only 파일. .gitignore에 포함되어 있으니 만들지 말 것.

---

## 8. 다른 프로젝트에 적용할 때 교체 포인트

| 항목 | 이 프로젝트 | 교체 |
|------|-------------|------|
| 도메인 컨텍스트 | 멀티모달 Vision AI (지엔소프트) | 사용자의 도메인 |
| 일정 | 8주 (2026-06~07) | 사용자의 일정 |
| 팀 구성 | 5팀 × 4명 | 사용자 팀 구성 |
| 산출물 | 기획서 + 프로토타입 | 사용자 산출물 |
| 기술 스택 | Python + uv + Gradio | 사용자 스택 |
| Subagent 5종 | VLM/RAG/Prototype/PublicData/Planning | 도메인 맞춤 |
| Skill 3종 | team-init/prototype-scaffold/planning-report | 도메인 맞춤 |
| 외부 도메인 화이트리스트 | hf/github/data.go.kr/gradio/... | 사용자 자주 쓰는 사이트 |

**CLAUDE.md / Subagent / Skill의 본문은 거의 그대로 두되, 위 8가지 컨텍스트만 갈아끼우면
다른 한국형 LLM·바이브 코딩 프로젝트에 즉시 재사용 가능**하다.

---

## 9. 체크리스트 (다른 AI가 작업 끝나고 확인할 항목)

- [ ] `CLAUDE.md` 존재, 프로젝트 한 줄 요약/일정/스택/컨벤션 포함
- [ ] `README.md` 빠른 시작 + 명령 표
- [ ] `pyproject.toml` ruff/pytest 설정 포함
- [ ] `.gitignore` Python+Claude artifacts 모두
- [ ] `.env.example` API 키 자리표시
- [ ] `.claude/settings.json` JSON 유효 + permissions/hooks/env 포함
- [ ] `.claude/hooks/format_py.py` exit 0 보장
- [ ] `.claude/hooks/session_start.py` hookSpecificOutput JSON 출력
- [ ] `.claude/agents/` 5개 .md, 각 frontmatter 유효
- [ ] `.claude/skills/<name>/SKILL.md` 3개, 각 frontmatter 유효
- [ ] 검증 스크립트 모두 통과
- [ ] git commit 자동으로 하지 않음 (사용자 요청 시만)
