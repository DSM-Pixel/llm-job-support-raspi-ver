// 업무 자동화 — 자연어 목표 → AI 에이전트가 업무 절차를 설계하고 기능에 연결.
(() => {
  const $ = (sel) => document.querySelector(sel);
  const input = $(".ag-input");
  const result = $(".ag-result");
  let steps = []; // 마지막 계획의 단계(첫 단계 이동용)

  const renderSteps = (list) => {
    $('[data-role="steps"]').innerHTML = list
      .map(
        (s) =>
          `<li class="ag-step card">` +
          `<div class="ag-step-num">${s.n}</div>` +
          `<div class="ag-step-body">` +
          `<div class="ag-step-top"><b>${ABC.escapeHtml(s.title)}</b>` +
          `<span class="ag-tool"><span class="ag-tool-ic">${ABC.escapeHtml(s.icon)}</span>${ABC.escapeHtml(s.tool_label)}</span></div>` +
          (s.why ? `<p class="ag-why">${ABC.escapeHtml(s.why)}</p>` : "") +
          `</div>` +
          `<a class="btn ag-step-go" href="${ABC.escapeHtml(s.route)}">이 단계 실행 →</a>` +
          `</li>`,
      )
      .join("");
  };

  const render = (data) => {
    steps = data.steps || [];
    $('[data-role="badge"]').outerHTML = `<span class="ag-badge" data-role="badge">${
      data.backend === "GEMINI" ? "AI 생성" : "기본 절차"
    }</span>`;
    $('[data-role="summary"]').textContent = data.summary;
    renderSteps(steps);
    const start = $('[data-role="start"]');
    if (steps.length) {
      start.hidden = false;
      start.onclick = () => (location.href = steps[0].route);
    } else {
      start.hidden = true;
    }
    result.hidden = false;
  };

  const plan = async (goal) => {
    const g = (goal ?? input.value).trim();
    if (!g) {
      ABC.toast("목표를 입력해주세요");
      return;
    }
    input.value = g;
    const restore = ABC.setBusy($(".ag-go"), "설계 중");
    try {
      const data = await ABC.api("/api/agent/plan", { goal: g });
      render(data);
      ABC.logActivity("업무 자동화", g);
    } catch {
      /* api() 가 이미 토스트 */
    } finally {
      restore();
    }
  };

  document.addEventListener("DOMContentLoaded", () => {
    $(".ag-go").addEventListener("click", () => plan());
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") plan();
    });
    document.querySelectorAll(".ag-chip").forEach((chip) => {
      chip.addEventListener("click", () => plan(chip.textContent.trim()));
    });

    // 이 화면에서 AI 대화는 '업무 절차' 관점으로.
    ABC.registerAskHandler(
      async (q) => (await ABC.api("/api/agent/plan", { goal: q })).summary,
      "업무 목표를 적으면 절차를 설계해 드려요",
    );

    // 자동 설계 금지 — 버튼을 눌러야 설계한다. 단, 다른 화면에서 ?q= 로
    // 넘어온 경우(명시적 의도)에만 자동 실행.
    const q = new URLSearchParams(location.search).get("q");
    if (q) plan(q);
  });
})();
