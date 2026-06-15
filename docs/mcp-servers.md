# MCP 서버 레지스트리 — llm-job-support

이 프로젝트에서 **앞으로 쓸 수 있는 / 쓰고 있는 MCP 서버**를 한 곳에 정리한 문서.

> **MCP(Model Context Protocol)** = Claude(또는 Claude Code)가 외부 도구·데이터에
> 표준 방식으로 연결되는 프로토콜. "서버" 하나가 곧 "도구 묶음 하나"다.
> 예: `memory` 서버 → `memory_save` / `memory_search` … 같은 도구를 제공.

## 📌 유지 규칙 (중요)

- **새 MCP 서버를 도입/설정할 때마다 이 파일에 한 줄(한 항목) 추가**한다.
- 항목에는 최소: **이름 · 무엇을 하나 · 제공 도구 · 설정 위치 · 상태**.
- 설정의 실제 진실은 `.mcp.json`(프로젝트 루트). 이 문서는 그 사람이 읽는 설명서.
- 더 이상 안 쓰는 서버는 지우지 말고 **`상태: 폐기`** 로 남겨 히스토리를 보존.

---

## ✅ 현재 등록된 MCP 서버

### 1. `memory` — 장기 기억 (세션 간 진행상황 유지)

| 항목 | 내용 |
|---|---|
| 무엇을 하나 | 세션이 바뀌어도 결정사항·진행상황을 SQLite에 저장/검색. 자동 로드 안 됨 → 평소 토큰 0. |
| 제공 도구 | `memory_save(content, tags)` · `memory_search(query)` · `memory_recent(limit)` · `memory_delete(id)` |
| 구현 | `.claude/mcp/memory_server.py` (Python stdlib만, 외부 패키지 0) |
| 저장소 | `.claude/memory.db` (SQLite, **커밋 금지** — `.gitignore` 처리됨) |
| 실행 | Python 3.11 (`.mcp.json`에 경로 명시) |
| 상태 | **사용 중** |

언제 쓰나: 세션 시작 시 `memory_search`로 맥락 복원, 중요한 사실/결정이 생기면 `memory_save`로 즉시 저장. 한 건 = 한 사실, 태그는 공백 구분.

---

## 🔭 앞으로 도입 후보 (아직 미설정)

프로젝트 성격(멀티모달 Vision AI / RAG / 공공데이터 / 보고서 자동화)에 맞는 후보들.
필요해지면 `.mcp.json`에 추가하고 위 "현재 등록" 섹션으로 승격시킨다.

| 후보 MCP | 무엇에 쓰나 | 우리 프로젝트 연결점 |
|---|---|---|
| **filesystem** | 지정 폴더 파일 읽기/쓰기 표준화 | `data/`, `docs/` 산출물 접근 |
| **fetch / web** | URL 가져와 본문 추출 | 공공데이터포털 문서, 논문/모델 카드 수집 |
| **sqlite** | 임의 SQLite DB 질의 | 라벨링 결과·메타데이터 저장/조회 |
| **chroma / 벡터DB** | 임베딩 색인·검색 | Hybrid RAG 지식검색 백엔드 |
| **time** | 현재시각·타임존 | 로그/보고서 타임스탬프 |
| **github** | 이슈/PR/코드 조회 | 팀 협업, 산출물 추적 |

> 위 후보들은 예시다. 실제 도입 전 **라이선스·보안(시크릿 노출)·Windows 호환성**을 확인할 것.

---

## ⚙️ MCP 추가하는 법 (요약)

1. 서버 준비: 직접 만든 stdio 스크립트(`memory_server.py`처럼) 또는 기존 npm/pip 패키지.
2. 프로젝트 루트 `.mcp.json`의 `mcpServers`에 항목 추가:
   ```json
   {
     "mcpServers": {
       "이름": { "command": "실행파일경로", "args": ["서버스크립트경로"] }
     }
   }
   ```
3. 시크릿이 필요하면 `env`로 주입(코드/.mcp.json에 키 하드코딩·커밋 금지 → `.env` 사용).
4. Claude Code에서 `/mcp`로 연결 확인.
5. **이 문서(`docs/mcp-servers.md`)에 새 항목 추가** ← 잊지 말 것.

---

_최초 작성: 2026-06-15 · 새 MCP 도입 시 갱신_
