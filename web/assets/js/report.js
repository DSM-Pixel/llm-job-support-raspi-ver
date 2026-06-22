document.addEventListener("DOMContentLoaded", () => {
  const esc = ABC.escapeHtml;
  const reportPage = document.querySelector(".report-page");

  document.querySelectorAll(".select-list button, .chips .pill").forEach((item) => {
    item.addEventListener("click", () =>
      ABC.activateInGroup(item, item.tagName === "BUTTON" ? "button" : ".pill"),
    );
  });

  document.querySelectorAll(".source-toggle .switch").forEach((switchEl) => {
    const row = switchEl.closest(".source-toggle");
    row?.classList.toggle("is-off", switchEl.classList.contains("off"));
    switchEl.addEventListener("click", () => {
      switchEl.classList.toggle("off");
      row?.classList.toggle("is-off", switchEl.classList.contains("off"));
    });
  });

  const activeSources = () =>
    [...document.querySelectorAll(".source-toggle")]
      .filter((row) => !row.querySelector(".switch")?.classList.contains("off"))
      .map((row) => row.querySelector("span, b")?.textContent.trim())
      .filter(Boolean);

  // 구조화 응답 → 편집 가능한 제출 보고서 문서로 렌더.
  const renderReport = (r) => {
    const sections = (r.sections || [])
      .map(
        (s) =>
          `<section><h3 contenteditable="true">${esc(s.heading)}</h3><p contenteditable="true">${esc(s.body)}</p></section>`,
      )
      .join("");

    let table = "";
    if (r.table) {
      const head = r.table.columns.map((c) => `<th>${esc(c)}</th>`).join("");
      const body = r.table.rows
        .map((row) => `<tr>${row.map((c) => `<td contenteditable="true">${esc(c)}</td>`).join("")}</tr>`)
        .join("");
      table = `<section><h3 contenteditable="true">${esc(r.table.caption)}</h3><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
    }

    const sources = (r.sources || [])
      .map((s) => `<span class="pill">${esc(s)}</span>`)
      .join("");

    reportPage.innerHTML = `
      <header>
        <p>${esc(r.org)} · ${esc(r.report_type)}</p>
        <h2 contenteditable="true">${esc(r.title)}</h2>
        <span>${esc(r.subtitle)}</span>
      </header>
      ${sections}
      ${table}
      <footer><b>출처</b>${sources}</footer>`;
  };

  const generate = async (button) => {
    const reportType =
      document.querySelector(".select-list .active")?.textContent.trim() || "현황 분석";
    const period = document.querySelector(".chips .active")?.textContent.trim() || "최근 3년";
    const done = button ? ABC.setBusy(button, "생성 중") : () => {};
    try {
      const result = await ABC.api("/api/report", {
        report_type: reportType,
        period,
        sources: activeSources(),
      });
      renderReport(result);
      if (button) ABC.toast("보고서를 생성했습니다 — 본문을 직접 수정할 수 있어요");
    } catch {
      /* api()가 toast */
    } finally {
      done();
    }
  };

  document.querySelector(".report-form .primary")?.addEventListener("click", (e) => generate(e.currentTarget));

  // 첫 진입 시 편집 가능한 문서로 한 번 렌더.
  generate(null);

  // 내보내기/공유는 (수정 반영된) 문서 전체 텍스트를 사용.
  const getReportText = () => reportPage?.innerText.trim() || "보고서";

  document.querySelector(".copy-report")?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(getReportText());
      ABC.toast("보고서 내용이 복사되었습니다");
    } catch {
      ABC.toast("복사를 지원하지 않는 브라우저입니다");
    }
  });

  document.querySelector(".pdf-report")?.addEventListener("click", () => window.print());

  document.querySelector(".share-report")?.addEventListener("click", async () => {
    const title = reportPage?.querySelector("h2")?.textContent.trim() || "보고서";
    const text = getReportText();
    try {
      if (navigator.share) {
        await navigator.share({ title, text });
        ABC.toast("공유를 완료했습니다");
        return;
      }
      await navigator.clipboard.writeText(text);
      ABC.toast("공유 기능이 없어 보고서 내용을 복사했습니다");
    } catch {
      ABC.toast("공유를 취소했거나 지원하지 않습니다");
    }
  });
});
