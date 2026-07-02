document.addEventListener("DOMContentLoaded", async () => {
  const dateEl = document.querySelector(".date");
  if (dateEl) {
    const today = new Date();
    const weekday = new Intl.DateTimeFormat("ko-KR", { weekday: "long" }).format(today);
    dateEl.textContent = `${today.getFullYear()}.${today.getMonth() + 1}.${today.getDate()} · ${weekday}`;
  }

  // ── 업무 자동화 위젯 — 목표 → /api/agent/plan → 절차 미리보기 ──
  // 각 단계는 해당 기능 화면으로 바로 이동(딥링크)할 수 있다.
  const agentGoal = document.querySelector(".agent-goal");
  const agentGo = document.querySelector(".agent-go");
  const agentSteps = document.querySelector(".agent-steps");
  const planAgent = async () => {
    const goal = agentGoal.value.trim();
    if (!goal) return ABC.toast("목표를 입력해주세요");
    const done = ABC.setBusy(agentGo, "설계 중");
    try {
      const d = await ABC.api("/api/agent/plan", { goal });
      agentSteps.innerHTML =
        (d.steps || [])
          .map(
            (s) =>
              `<li><span class="agent-num">${s.n}</span><div class="agent-body"><b>${ABC.escapeHtml(s.title)}</b><small>${ABC.escapeHtml(s.icon)} ${ABC.escapeHtml(s.tool_label)}</small></div><a class="agent-run" href="${ABC.escapeHtml(s.route)}">실행 →</a></li>`,
          )
          .join("") || '<li class="agent-empty">절차를 만들지 못했습니다. 다시 시도해주세요.</li>';
      ABC.logActivity("업무 자동화", goal);
    } catch {
      /* api()가 toast */
    } finally {
      done();
    }
  };
  agentGo?.addEventListener("click", planAgent);
  agentGoal?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") planAgent();
  });

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

    // 상단 통계 카드는 renderRealStats()가 실제 값으로 채운다(MOCK data.stats 미사용).
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

  // ── 최근 활동은 실제 사용 기록(localStorage)으로 ─────────────────
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
    }
  } catch {
    /* 활동 기록 읽기 실패 시 서버/기본값 유지 */
  }

  // ── 상단 통계 4개를 '실제 값'으로 교체 (현재 프로젝트 기준) ──────
  // ① 색인 문서·청크 = RAG 파일(API)  ② 내 작업물 = 저장 아티팩트(localStorage)
  // ③ 오늘 처리 작업 = 오늘 활동 수     ④ 총 활동 = 누적 활동 수
  // (실측 불가한 mAP 대신 실제 집계 가능한 값으로 대체)
  const statCard = (icon, value, label, sub) =>
    `<article class="card stat-card"><span class="icon-box">${icon}</span><strong>${value}</strong><p>${ABC.escapeHtml(label)}</p><small>${ABC.escapeHtml(sub)}</small></article>`;

  const renderRealStats = async () => {
    const grid = document.querySelector(".stat-grid");
    if (!grid) return;
    const acts = ABC.getActivity ? ABC.getActivity() : [];
    const arts = ABC.getArtifacts ? ABC.getArtifacts() : [];
    // 오늘 0시 이후 활동.
    const dayStart = new Date();
    dayStart.setHours(0, 0, 0, 0);
    const todayCnt = acts.filter((a) => a.ts >= dayStart.getTime()).length;
    // 작업물: 라벨/분석 이미지 vs RAG 결과 구분.
    const imgArts = arts.filter((a) => a.kind === "image").length;
    const ragArts = arts.filter((a) => a.kind === "rag").length;

    // RAG 색인 문서·청크(현재 프로젝트) — API.
    let files = 0;
    let chunks = 0;
    try {
      const pid = (ABC.getProject && ABC.getProject()) ? ABC.getProject().id : "";
      const r = await ABC.api(`/api/rag/files?project=${encodeURIComponent(pid)}`);
      files = (r.files || []).length;
      chunks = (r.files || []).reduce((s, f) => s + (f.chunks || 0), 0);
    } catch {
      /* 서버 미연결 시 0 */
    }

    grid.innerHTML =
      statCard("▱", files.toLocaleString(), "색인 문서·소스", `청크 ${chunks.toLocaleString()}개`) +
      statCard("⬡", imgArts.toLocaleString(), "라벨·분석 작업물", `RAG 결과 ${ragArts}건`) +
      statCard("⌁", todayCnt.toLocaleString(), "오늘 처리 작업", "질의·검색·라벨 등") +
      statCard("◷", acts.length.toLocaleString(), "총 활동 기록", "이 프로젝트 누적");
    grid.querySelectorAll(".stat-card strong").forEach(countUp);
  };
  renderRealStats();

  const routes = ["rag.html", "labeling.html", "report.html", "query.html"];
  document.querySelectorAll(".quick-grid button").forEach((button, index) => {
    button.addEventListener("click", () => {
      window.location.href = routes[index];
    });
  });

  // ── 히어로 질문창(허브) — 질문을 자연어 질의로 보내면 거기서 자동 분류·연계 ──
  // (route_query 가 일반답변/문서검색/이미지분석/통계로 알아서 라우팅한다)
  const heroInput = document.querySelector(".hero-ask-input");
  const heroGo = document.querySelector(".hero-ask-go");
  const heroAsk = () => {
    const q = heroInput.value.trim();
    if (!q) return ABC.toast("질문을 입력해주세요");
    window.location.href = `query.html?q=${encodeURIComponent(q)}`;
  };
  heroGo?.addEventListener("click", heroAsk);
  heroInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") heroAsk();
  });

  // 최근 활동 '전체 기록 →' = 기록 관리 모달(같은 데이터의 전체 보기·삭제).
  document.querySelector(".history-link")?.addEventListener("click", ABC.openHistory);
});
