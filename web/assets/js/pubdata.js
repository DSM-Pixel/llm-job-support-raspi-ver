// 공공데이터 연계 — 키워드로 data.go.kr 데이터셋·통계·요약을 불러와 시각화.
(() => {
  const $ = (sel) => document.querySelector(sel);
  const input = $(".pd-input");
  const result = $(".pd-result");
  let current = null; // 마지막 검색 결과(AI 패널·보고서 전송용)

  const badgeFor = (backend) =>
    backend === "GEMINI"
      ? '<span class="pd-badge live">AI 생성</span>'
      : '<span class="pd-badge mock">템플릿</span>';

  // 값 배열 → CSS 막대 차트. 최고값을 100%로 정규화.
  const renderBars = (stats) => {
    const max = Math.max(1, ...stats.values);
    const bars = $('[data-role="bars"]');
    bars.innerHTML = stats.labels
      .map((label, i) => {
        const v = stats.values[i];
        const pct = Math.round((v / max) * 100);
        const hot = v === max ? " hot" : "";
        return (
          `<div class="pd-bar-col" title="${ABC.escapeHtml(label)}: ${v}${ABC.escapeHtml(stats.unit)}">` +
          `<span class="pd-bar-val">${v}</span>` +
          `<div class="pd-bar${hot}" style="height:${Math.max(4, pct)}%"></div>` +
          `<span class="pd-bar-label">${ABC.escapeHtml(label)}</span>` +
          `</div>`
        );
      })
      .join("");
    $('[data-role="chart-title"]').textContent = `${stats.title}`;
  };

  const renderDatasets = (datasets) => {
    $('[data-role="ds-count"]').textContent = `${datasets.length} sets · data.go.kr`;
    $('[data-role="datasets"]').innerHTML = datasets
      .map(
        (d) =>
          `<a class="pd-ds card" href="${d.url}" target="_blank" rel="noopener">` +
          `<div class="pd-ds-main"><b>${ABC.escapeHtml(d.title)}</b>` +
          `<p>${ABC.escapeHtml(d.provider)} 제공</p></div>` +
          `<div class="pd-ds-meta"><span class="pd-tag">${ABC.escapeHtml(d.category)}</span>` +
          `<span class="pd-fmt">${ABC.escapeHtml(d.format)}</span></div>` +
          `<span class="pd-ds-open">↗</span></a>`,
      )
      .join("");
  };

  const render = (data) => {
    current = data;
    $('[data-role="domain"]').textContent = data.domain;
    $('[data-role="summary"]').textContent = data.summary;
    $('[data-role="summary-badge"]').outerHTML = `<span class="pd-badge" data-role="summary-badge">${
      data.summary_backend === "GEMINI" ? "AI 생성" : "템플릿"
    }</span>`;
    $('[data-role="insights"]').innerHTML = (data.insights || [])
      .map((t) => `<li>${ABC.escapeHtml(t)}</li>`)
      .join("");
    renderBars(data.stats);
    // 차트 출처 데이터셋 + 실데이터/샘플 배지.
    const badge = data.stats.sample
      ? '<span class="pd-badge sample">샘플 통계</span>'
      : '<span class="pd-badge live">실데이터(data.go.kr)</span>';
    $('[data-role="chart-src"]').innerHTML = `출처: ${ABC.escapeHtml(data.stats.dataset || "")} ${badge}`;
    renderDatasets(data.datasets);
    const portal = $(".pd-portal");
    portal.href = data.portal_url;
    result.hidden = false;

    // AI 패널이 이 통계를 근거로 답하도록 스코프 등록.
    const ctx =
      `주제 ${data.domain}. ${data.stats.title}: ` +
      data.stats.labels.map((l, i) => `${l}=${data.stats.values[i]}`).join(", ") +
      `. 요약: ${data.summary}`;
    ABC.registerAskHandler(
      async (q) => (await ABC.api("/api/ask/context", { context: ctx, question: q })).answer,
      `‘${data.domain}’ 공공데이터 통계에 대해 물어보세요`,
    );
  };

  const search = async (keyword) => {
    const kw = (keyword ?? input.value).trim();
    if (!kw) {
      ABC.toast("검색어를 입력해주세요");
      return;
    }
    input.value = kw;
    const restore = ABC.setBusy($(".pd-go"), "불러오는 중");
    try {
      const data = await ABC.api("/api/pubdata/search", { keyword: kw });
      render(data);
      ABC.logActivity("공공데이터 연계", kw);
    } catch {
      /* api() 가 이미 토스트 */
    } finally {
      restore();
    }
  };

  // 이 통계 요약을 보고서 '내 작업에서 가져오기'로 넘긴다(기존 아티팩트 파이프 재사용).
  const sendToReport = () => {
    if (!current) return;
    ABC.saveArtifact({
      kind: "rag",
      title: `공공데이터 · ${current.domain}`,
      question: `${current.keyword} 관련 공공데이터 통계`,
      answer: current.summary,
      source: current.datasets[0]?.title || "data.go.kr",
      snippet: current.stats.title,
    });
    ABC.toast("보고서 자료로 저장했습니다");
    window.setTimeout(() => (location.href = "report.html"), 500);
  };

  // 등록된 전체 데이터셋 현황(확장형 구조를 화면에 드러냄).
  const loadCatalog = async () => {
    try {
      const c = await ABC.api("/api/pubdata/catalog");
      const domains = new Set(c.datasets.map((d) => d.domain)).size;
      const mode = c.live ? "실데이터 연계" : "샘플(키 미등록)";
      $('[data-role="catalog"]').textContent =
        `▤ 현재 ${c.total}개 공공데이터셋 · ${domains}개 도메인 연동 중 (${c.loaded}개 적재 · ${mode}). 데이터셋은 레지스트리에 설정만 추가하면 늘어납니다.`;
    } catch {
      /* 무시 */
    }
  };

  document.addEventListener("DOMContentLoaded", () => {
    loadCatalog();
    $(".pd-go").addEventListener("click", () => search());
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") search();
    });
    document.querySelectorAll(".pd-chip").forEach((chip) => {
      chip.addEventListener("click", () => search(chip.textContent.trim()));
    });
    $(".pd-to-report").addEventListener("click", sendToReport);

    // ?q= 로 들어오면 그 키워드로 자동 검색(자연어 질의·다른 화면에서 연계).
    const q = new URLSearchParams(location.search).get("q");
    search(q || input.value);
  });
})();
