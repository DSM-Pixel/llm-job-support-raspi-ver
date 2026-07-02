---
description: GitHub 이슈 번호를 받아 해당 이슈를 분석하고 수정 (브랜치 생성 → 수정 → 검증)
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

GitHub 이슈 #$ARGUMENTS 를 수정해라. (리포: DSM-Pixel/llm-job-support)

## 절차

1. **이슈 읽기**: `gh issue view $ARGUMENTS --comments` 로 본문·댓글·라벨 확인. 번호가 없거나 이슈가 안 열리면 멈추고 사용자에게 묻는다.
2. **브랜치**: main 직접 커밋 금지 정책 — `git switch -c fix/issue-$ARGUMENTS-<짧은설명>` (이미 관련 브랜치에 있으면 그대로 진행).
3. **원인 분석**: 이슈에 언급된 증상을 코드에서 재현/추적한다. 관련 규칙 준수:
   - `backend/` → `.claude/rules/api-design.md` (어댑터 계층, RPi5 제약)
   - `web/` → `.claude/rules/frontend.md` (기존 구조 유지, 프레임워크 도입 금지)
   - RAG → `.claude/rules/rag.md`
4. **수정**: 이슈 범위만 고친다. 겸사겸사 리팩터링 금지.
5. **검증**:
   - `uv run pytest` (테스트 있으면)
   - 해당 기능을 `/run` 방식으로 실제 띄워 확인 — 이슈의 재현 절차를 그대로 따라 해본다.
6. **커밋**: 한국어, 동사 시작, 이슈 참조 포함 — 예: `RAG 검색 빈 질의 500 에러 수정 (#$ARGUMENTS)`. **push·PR 생성은 사용자에게 확인 후에만.**
7. **보고**: 원인 1줄 / 수정 파일 목록 / 검증 결과 / (원하면) PR 생성 제안. PR 본문에는 `Closes #$ARGUMENTS` 포함.

## 주의

- `.env`·시크릿을 절대 출력·커밋하지 않는다.
- 이슈가 기능 요청(버그 아님)이면 수정 전에 구현 방향을 한 번 요약해 사용자 동의를 받는다.
- 라이선스(AGPL-3.0) 관련 파일은 건드리지 않는다.
