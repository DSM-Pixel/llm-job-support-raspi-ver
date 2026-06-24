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

  // 모델 사용 현황 상세 모달(Gemini 등).
  let modelModal = null;
  const openModelDetail = (m) => {
    if (!modelModal) {
      modelModal = document.createElement("div");
      modelModal.className = "modal-overlay";
      modelModal.hidden = true;
      modelModal.innerHTML =
        '<div class="modal"><header class="modal-head"><h3 class="mm-title"></h3>' +
        '<button class="modal-close" type="button" aria-label="닫기">✕</button></header>' +
        '<div class="modal-body"><div class="mm-body"></div></div></div>';
      document.body.appendChild(modelModal);
      const close = () => {
        modelModal.hidden = true;
      };
      modelModal.querySelector(".modal-close").addEventListener("click", close);
      modelModal.addEventListener("click", (e) => {
        if (e.target === modelModal) close();
      });
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modelModal && !modelModal.hidden) close();
      });
    }
    modelModal.querySelector(".mm-title").textContent = `${m.name} · 사용 현황`;
    modelModal.querySelector(".mm-body").innerHTML = (m.detail || [])
      .map((d) => {
        // 안내 문구(note)는 전체 폭 캡션으로.
        if (d.note) return `<p class="mm-note">${ABC.escapeHtml(d.note)}</p>`;
        const k = ABC.escapeHtml(d.k);
        const v = ABC.escapeHtml(d.v);
        // 퍼센트(pct)가 있으면 막대로 — 한도 사용률을 시각화.
        if (typeof d.pct === "number") {
          const lvl = d.pct >= 90 ? " crit" : d.pct >= 70 ? " warn" : "";
          return `<div class="mm-row mm-bar-row"><div class="mm-bar-top"><span>${k}</span><b>${v}</b></div><i class="mm-bar${lvl}"><span style="width:${Math.min(100, d.pct)}%"></span></i></div>`;
        }
        return `<div class="mm-row"><span>${k}</span><b>${v}</b></div>`;
      })
      .join("");
    modelModal.hidden = false;
  };

  // 모델 상태 렌더(폴링으로 실시간 갱신). dashModels 는 클릭 상세에서 사용.
  let dashModels = [];
  const renderModels = (models) => {
    const card = document.querySelector(".model-card");
    if (!card || !models) return;
    dashModels = models;
    const rows = models
      .map((m, i) => {
        const click = m.detail ? " model-row-click" : "";
        const more = m.detail ? '<small class="model-more">탭하여 사용 현황 보기 ›</small>' : "";
        return `<div class="model-row${click}" data-idx="${i}" ${m.detail ? 'title="클릭하면 사용 현황 상세"' : ""}><span class="dot ${m.tone}"></span><div><b>${ABC.escapeHtml(m.name)}</b>${more}</div><i${m.tone === "orange" ? ' class="orange"' : ""}><span style="width: ${m.load}%"></span></i><em class="status ${m.tone}">${ABC.escapeHtml(m.state)}</em></div>`;
      })
      .join("");
    card.querySelectorAll(".model-row").forEach((row) => row.remove());
    card.insertAdjacentHTML("beforeend", rows);
  };
  // 모델 행 클릭(델리게이션, 한 번만 등록) → 사용 현황 상세.
  document.querySelector(".model-card")?.addEventListener("click", (e) => {
    const row = e.target.closest(".model-row-click");
    if (!row) return;
    const m = dashModels[Number(row.dataset.idx)];
    if (m && m.detail) openModelDetail(m);
  });

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

    renderModels(data.models);

    const activity = document.querySelector(".activity-card ul");
    if (activity && data.activity) {
      activity.innerHTML = data.activity
        .map((a) => `<li><span class="activity-icon">${a.icon}</span><b>${ABC.escapeHtml(a.text)}</b><small>${ABC.escapeHtml(a.meta)}</small></li>`)
        .join("");
    }
  } catch {
    /* 서버 미연결 시 HTML 기본값 그대로 사용 */
  }

  // 모델 상태(특히 Gemini 토큰·한도)를 12초마다 실시간 갱신.
  setInterval(async () => {
    try {
      const d = await ABC.api("/api/dashboard");
      renderModels(d.models);
    } catch {
      /* 일시적 실패는 무시 */
    }
  }, 12000);

  // ── 주간 처리량·최근 활동은 실제 사용 기록(localStorage)으로 ──────
  // 통계 카드 수치(색인·라벨 등)는 MOCK 유지, 활동 기반 부분만 실데이터로 교체.
  const ACT_ICON = {
    "자연어 질의": "☰",
    "RAG 검색": "⌕",
    "문서 색인": "▱",
    "이미지 분석": "⌗",
    "라벨 저장": "⌗",
    "데이터 업로드": "▱",
  };
  const relTime = (ts) => {
    const s = Math.floor((Date.now() - ts) / 1000);
    if (s < 60) return "방금";
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}분 전`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}시간 전`;
    return `${Math.floor(h / 24)}일 전`;
  };

  try {
    const acts = ABC.getActivity ? ABC.getActivity() : [];
    if (acts.length) {
      // 최근 활동(최신 6개) — 실제 내가 한 작업.
      const activity = document.querySelector(".activity-card ul");
      if (activity) {
        activity.innerHTML = acts
          .slice(-6)
          .reverse()
          .map((a) => {
            const icon = ACT_ICON[a.type] || "•";
            const label = a.label ? ` — ${a.label}` : "";
            return `<li><span class="activity-icon">${icon}</span><b>${ABC.escapeHtml(a.type + label)}</b><small>${ABC.escapeHtml(a.page || "")} · ${relTime(a.ts)}</small></li>`;
          })
          .join("");
      }
      // 주간 처리량 — 최근 7일 일별 활동 건수.
      const chart = document.querySelector(".chart-bars");
      if (chart) {
        const now = new Date();
        const days = [];
        for (let i = 6; i >= 0; i--) {
          const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
          const start = d.getTime();
          const end = start + 86400000;
          const count = acts.filter((a) => a.ts >= start && a.ts < end).length;
          const wd = new Intl.DateTimeFormat("ko-KR", { weekday: "short" }).format(d);
          days.push({ day: wd, count });
        }
        const max = Math.max(1, ...days.map((d) => d.count));
        chart.innerHTML = days
          .map(
            (d) =>
              `<div class="bar-item"><span style="height:${d.count ? Math.max(8, Math.round((d.count / max) * 100)) : 2}%" title="${d.count}건"></span><b>${d.day}</b></div>`,
          )
          .join("");
      }
    }
  } catch {
    /* 활동 기록 읽기 실패 시 서버/기본값 유지 */
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
