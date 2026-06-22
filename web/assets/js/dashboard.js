document.addEventListener("DOMContentLoaded", async () => {
  const dateEl = document.querySelector(".date");
  if (dateEl) {
    const today = new Date();
    const weekday = new Intl.DateTimeFormat("ko-KR", { weekday: "long" }).format(today);
    dateEl.textContent = `${today.getFullYear()}.${today.getMonth() + 1}.${today.getDate()} · ${weekday}`;
  }

  const countUp = (value) => {
    const raw = value.textContent.replace(/,/g, "");
    const target = Number.parseFloat(raw);
    if (Number.isNaN(target)) return;
    const suffix = value.textContent.includes("%") ? "%" : "";
    let frame = 0;
    const tick = () => {
      frame += 1;
      const next = target * Math.min(frame / 24, 1);
      value.textContent = target < 10 ? next.toFixed(3) : Math.round(next).toLocaleString("ko-KR") + suffix;
      if (frame < 24) requestAnimationFrame(tick);
    };
    tick();
  };

  // 대시보드 데이터를 서버에서 받아 렌더링. 실패 시 HTML 기본값 유지.
  try {
    const data = await ABC.api("/api/dashboard");

    const statGrid = document.querySelector(".stat-grid");
    if (statGrid && data.stats) {
      statGrid.innerHTML = data.stats
        .map((s) => `<article class="card stat-card"><span class="icon-box">${s.icon}</span><em>${s.delta}</em><strong>${s.value}</strong><p>${ABC.escapeHtml(s.label)}</p><small>${ABC.escapeHtml(s.sub)}</small></article>`)
        .join("");
    }

    const chart = document.querySelector(".chart-bars");
    if (chart && data.weekly) {
      chart.innerHTML = data.weekly
        .map((w) => `<div class="bar-item"><span style="height: ${w.value}%"></span><b>${w.day}</b></div>`)
        .join("");
    }

    const modelCard = document.querySelector(".model-card");
    if (modelCard && data.models) {
      const rows = data.models
        .map((m) => `<div class="model-row"><span class="dot ${m.tone}"></span><div><b>${ABC.escapeHtml(m.name)}</b><small>${ABC.escapeHtml(m.kind)}</small></div><i${m.tone === "orange" ? ' class="orange"' : ""}><span style="width: ${m.load}%"></span></i><em class="status ${m.tone}">${ABC.escapeHtml(m.state)}</em></div>`)
        .join("");
      modelCard.querySelectorAll(".model-row").forEach((row) => row.remove());
      modelCard.insertAdjacentHTML("beforeend", rows);
    }

    const activity = document.querySelector(".activity-card ul");
    if (activity && data.activity) {
      activity.innerHTML = data.activity
        .map((a) => `<li><span class="activity-icon">${a.icon}</span><b>${ABC.escapeHtml(a.text)}</b><small>${ABC.escapeHtml(a.meta)}</small></li>`)
        .join("");
    }
  } catch {
    /* 서버 미연결 시 HTML 기본값 그대로 사용 */
  }

  document.querySelectorAll(".stat-card strong").forEach(countUp);

  const routes = ["rag.html", "labeling.html", "report.html", "query.html"];
  document.querySelectorAll(".quick-grid button").forEach((button, index) => {
    button.addEventListener("click", () => {
      window.location.href = routes[index];
    });
  });

  document.querySelector(".hero-row .primary")?.addEventListener("click", () => {
    window.location.href = "query.html";
  });
});
