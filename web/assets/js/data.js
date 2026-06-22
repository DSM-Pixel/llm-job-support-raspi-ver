document.addEventListener("DOMContentLoaded", async () => {
  const tbody = document.querySelector("tbody");
  const search = document.querySelector(".search-upload input");

  const ICONS = { 라벨: "◇", 원본: "▧", 공공데이터: "▱", 문서: "▤" };

  const rowHtml = (d) => `<tr>
    <td><input type="checkbox"></td>
    <td><b class="name-cell"><span class="name-icon">${ICONS[d.kind] || "▱"}</span>${ABC.escapeHtml(d.name)}</b></td>
    <td>${ABC.escapeHtml(d.kind)}</td>
    <td>${ABC.escapeHtml(d.count)}</td>
    <td class="mono">${ABC.escapeHtml(d.fmt)}</td>
    <td><span class="status ${d.tone}">${ABC.escapeHtml(d.state)}</span></td>
    <td>${ABC.escapeHtml(d.date)}<small>${ABC.escapeHtml(d.owner)}</small></td>
    <td>⋮</td></tr>`;

  // 서버에서 데이터셋 목록을 받아 테이블을 채운다. 실패 시 HTML 기본 행 유지.
  try {
    const data = await ABC.api("/api/datasets");
    if (tbody && data.datasets) {
      tbody.innerHTML = data.datasets.map(rowHtml).join("");
    }
  } catch {
    /* 기본 행 사용 */
  }

  const rows = [...document.querySelectorAll("tbody tr")];

  const filterRows = () => {
    const keyword = (search?.value || "").trim().toLowerCase();
    const active = document.querySelector(".chips .active")?.textContent.trim();
    rows.forEach((row) => {
      const text = row.textContent.toLowerCase();
      const type = row.children[2]?.textContent.trim();
      const matchesKeyword = !keyword || text.includes(keyword);
      const matchesType =
        active === "전체" || type === active || (active === "원본 이미지" && type === "원본");
      row.hidden = !(matchesKeyword && matchesType);
    });
  };

  document.querySelectorAll(".chips .pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      ABC.activateInGroup(pill, ".pill");
      filterRows();
    });
  });

  search?.addEventListener("input", filterRows);

  document.querySelector("thead input[type='checkbox']")?.addEventListener("change", (event) => {
    document.querySelectorAll("tbody input[type='checkbox']").forEach((checkbox) => {
      checkbox.checked = event.target.checked;
    });
  });

  document.querySelector(".search-upload .primary")?.addEventListener("click", async (event) => {
    const done = ABC.setBusy(event.currentTarget, "업로드 중");
    try {
      const result = await ABC.api("/api/datasets/upload", { name: "" });
      ABC.toast(result.message || "업로드 대기열에 추가되었습니다");
    } catch {
      /* handled */
    } finally {
      done();
    }
  });
});
