export const meta = {
  name: 'daily-sync',
  description: '변경사항 요약 → 4대 데모 시나리오 점검 → docs/ 진행상황 갱신을 순차 실행',
  whenToUse: '하루 작업을 마무리할 때. 사용자가 "일일 싱크 돌려줘" / "오늘 정리해줘"라고 하면 실행.',
  phases: [
    { title: '변경 요약', detail: 'git log/diff로 오늘 변경사항 정리' },
    { title: '데모 점검', detail: '4대 데모 시나리오 end-to-end 상태 확인' },
    { title: '문서 갱신', detail: 'docs/notes/ 진행상황 노트 갱신' },
  ],
}

// 날짜는 스크립트 안에서 Date 사용 불가 → args로 받는다.
// 실행 예: Workflow({ name: 'daily-sync', args: { date: '2026-07-02' } })
const date = (args && args.date) || '(날짜 미지정 — args.date 로 전달)'

// ── 1단계: 변경사항 요약 ─────────────────────────────────────
phase('변경 요약')
const summary = await agent(
  `llm-job-support 리포의 오늘 변경사항을 요약해라.
- git log --oneline -20 과 git diff --stat HEAD~5 (커밋이 적으면 범위 축소), git status 를 확인.
- 영역별(backend/ · web/ · prototypes/ · docs/)로 무엇이 왜 바뀌었는지 한국어로 정리.
- 팀 우선순위(공공데이터 RAG, RPi5 서버 검증, 디자인 HTML→web/ 통합) 관점에서 진척을 한 줄씩 평가.
- 마지막 텍스트가 그대로 다음 단계 입력이 된다. 사람 인사말 없이 요약 본문만 반환.`,
  { label: 'summarize-changes', phase: '변경 요약' }
)

// ── 2단계: 4대 데모 시나리오 점검 ────────────────────────────
phase('데모 점검')
const demoReport = await agent(
  `.claude/commands/demo-check.md 의 절차대로 4대 데모 시나리오가 end-to-end로 도는지 점검해라:
1. "포트홀 영역을 찾아줘" 2. "공공데이터포털 기반으로 관련 통계를 보여줘"
3. "검색 결과를 요약해서 보고서로 만들어줘" 4. "업무 절차를 자동으로 추천해줘"
- 서버가 안 떠 있으면 ./run_web.sh 로 띄우고, curl로 실제 API를 호출해 판정(PASS/PARTIAL/FAIL + MOCK 여부).
- 절대 코드를 수정하지 말 것. 점검 결과 표와 FAIL/PARTIAL 원인만 반환.
- 참고 — 오늘 변경사항: ${JSON.stringify(String(summary).slice(0, 1500))}`,
  { label: 'demo-check', phase: '데모 점검' }
)

// ── 3단계: docs/ 진행상황 갱신 ───────────────────────────────
phase('문서 갱신')
const docResult = await agent(
  `docs/notes/ 에 일일 진행상황 노트를 갱신해라.
- 파일: docs/notes/${date}_작업노트.md — 이미 있으면 그 파일에 덧붙이고, 없으면 기존 노트(docs/notes/2026-06-17_작업노트.md 등)의 형식을 따라 새로 만든다.
- 내용: (1) 오늘 변경 요약 (2) 데모 시나리오 점검 결과 표 (3) 내일 할 일 제안 3개 이내.
- git commit 은 하지 말 것. 파일 작성만.

[변경 요약]
${String(summary).slice(0, 3000)}

[데모 점검 결과]
${String(demoReport).slice(0, 3000)}`,
  { label: 'update-docs', phase: '문서 갱신' }
)

return {
  date,
  summary,
  demoReport,
  docNote: docResult,
}
