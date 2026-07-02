// 프로젝트(노트북) — 작업을 프로젝트 단위로 나누고, 소스별 검수 상태를 관리.
(() => {
  const $ = (s) => document.querySelector(s);
  const gallery = $('[data-role="gallery"]');
  const detail = $('[data-role="detail"]');
  const grid = $('[data-role="grid"]');
  const REVIEW_TONE = { 대기: "wait", 승인: "ok", 반려: "no" };
  const EMOJIS = ["📁", "🛣️", "🏗️", "📹", "📊", "🚧", "🧭", "🗂️"];

  const reviewer = () => (ABC.getSettings().name || "검수자");

  // ── 간단 입력 모달(프로젝트/소스 생성) ──
  const askInput = (title, fields) =>
    new Promise((resolve) => {
      const ov = document.createElement("div");
      ov.className = "modal-overlay";
      ov.innerHTML =
        `<div class="modal"><header class="modal-head"><h3>${ABC.escapeHtml(title)}</h3>` +
        `<button class="modal-close" type="button">✕</button></header>` +
        `<div class="modal-body"><div class="modal-form">` +
        fields.map((f) => f.html).join("") +
        `</div></div><div class="modal-foot">` +
        `<button class="btn modal-cancel" type="button">취소</button>` +
        `<button class="btn primary modal-ok" type="button">확인</button></div></div>`;
      document.body.appendChild(ov);
      const close = (val) => {
        ov.remove();
        resolve(val);
      };
      ov.querySelector(".modal-close").onclick = () => close(null);
      ov.querySelector(".modal-cancel").onclick = () => close(null);
      ov.addEventListener("click", (e) => e.target === ov && close(null));
      ov.querySelector(".modal-ok").onclick = () => {
        const out = {};
        ov.querySelectorAll("[data-name]").forEach((el) => (out[el.dataset.name] = el.value.trim()));
        close(out);
      };
      ov.querySelector("input,select")?.focus();
    });

  // ── 갤러리 ──
  let galleryProjects = [];
  const renderGallery = (projects) => {
    galleryProjects = projects;
    const cards = projects
      .map((p) => {
        const bar = `<div class="pj-card-bar"><span style="width:${p.progress}%"></span></div>`;
        return (
          `<article class="pj-card" data-enter="${p.id}" title="이 프로젝트로 들어가기">` +
          `<button class="pj-card-del" data-del="${p.id}" title="프로젝트 삭제">✕</button>` +
          `<div class="pj-card-emoji">${ABC.escapeHtml(p.emoji)}</div>` +
          `<b class="pj-card-name">${ABC.escapeHtml(p.name)}</b>` +
          `<small class="pj-card-meta">소스 ${p.source_count}개 · 검수 ${p.approved}/${p.source_count}</small>` +
          bar +
          `<div class="pj-card-foot"><small class="pj-card-progress">검수 진행률 ${p.progress}%</small>` +
          `<button class="pj-card-manage" data-manage="${p.id}">소스·검수 →</button></div>` +
          `</article>`
        );
      })
      .join("");
    grid.innerHTML =
      `<button class="pj-card pj-new" data-role="new"><span class="pj-new-plus">+</span>새 프로젝트 만들기</button>` +
      cards;
  };

  // 프로젝트로 '진입' — 현재 프로젝트로 설정하고 작업 공간(대시보드)으로.
  const enterProject = (pid) => {
    const p = galleryProjects.find((x) => x.id === pid) || (currentDetail && currentDetail.id === pid ? currentDetail : null);
    if (!p) return;
    ABC.setProject({ id: p.id, name: p.name, emoji: p.emoji });
    ABC.toast(`‘${p.name}’ 프로젝트로 전환`);
    location.href = "dashboard.html";
  };

  const loadGallery = async () => {
    try {
      const data = await ABC.api("/api/projects");
      renderGallery(data.projects || []);
    } catch {
      /* toast in api() */
    }
  };

  const showGallery = () => {
    detail.hidden = true;
    gallery.hidden = false;
    history.replaceState(null, "", location.pathname);
    loadGallery();
  };

  // ── 상세(소스 + 검수) ──
  const renderDetail = (p) => {
    $('[data-role="d-emoji"]').textContent = p.emoji;
    $('[data-role="d-name"]').textContent = p.name;
    $('[data-role="d-progress-label"]').textContent = `검수 ${p.approved}/${p.source_count} · ${p.progress}%`;
    $('[data-role="d-progress-bar"]').style.width = `${p.progress}%`;
    $('[data-role="src-list"]').innerHTML = (p.sources || [])
      .map((s) => {
        const tone = REVIEW_TONE[s.review] || "wait";
        const who = s.reviewer ? `${ABC.escapeHtml(s.reviewer)} · ${ABC.relTime(s.reviewed_at)}` : "미검수";
        const btn = (st, label, cls) =>
          `<button class="pj-rv-btn ${cls}${s.review === st ? " on" : ""}" data-review="${s.id}" data-status="${st}">${label}</button>`;
        return (
          `<div class="pj-src">` +
          `<span class="pj-src-kind">${ABC.escapeHtml(s.kind)}</span>` +
          `<div class="pj-src-main"><b>${ABC.escapeHtml(s.name)}</b><small>검수자 ${who}</small></div>` +
          `<span class="pj-badge ${tone}">${ABC.escapeHtml(s.review)}</span>` +
          `<div class="pj-rv-btns">${btn("승인", "승인", "ok")}${btn("반려", "반려", "no")}${btn("대기", "대기", "wait")}</div>` +
          `</div>`
        );
      })
      .join("") || '<p class="pj-empty">아직 소스가 없습니다. ‘+ 소스 추가’로 데이터를 넣어보세요.</p>';
  };

  let currentPid = null;
  let currentDetail = null;
  const openProject = async (pid) => {
    try {
      const p = await ABC.api(`/api/projects/${pid}`);
      if (p.error) return showGallery();
      currentPid = pid;
      currentDetail = p;
      gallery.hidden = true;
      detail.hidden = false;
      history.replaceState(null, "", `?p=${pid}`);
      renderDetail(p);
    } catch {
      /* toast */
    }
  };

  const setReview = async (sourceId, status) => {
    try {
      const p = await ABC.api("/api/review", { source_id: sourceId, status, reviewer: reviewer() });
      if (!p.error) {
        renderDetail(p);
        ABC.logActivity("검수", `${status}`);
      }
    } catch {
      /* toast */
    }
  };

  // ── 이벤트 위임 ──
  document.addEventListener("DOMContentLoaded", () => {
    // 로고 클릭 → 프로젝트 목록으로(상세 보던 중이면 목록으로 나감).
    document.querySelector(".pj-logo")?.addEventListener("click", showGallery);

    // 아바타 클릭 → 프로필(이름·소속) 모달.
    const avatar = document.querySelector(".pj-top .avatar");
    avatar?.addEventListener("click", ABC.openSettings);
    avatar?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        ABC.openSettings();
      }
    });

    $('[data-role="back"]').addEventListener("click", showGallery);
    $('[data-role="enter"]').addEventListener("click", () => currentPid && enterProject(currentPid));

    grid.addEventListener("click", async (e) => {
      const del = e.target.closest("[data-del]");
      if (del) {
        e.stopPropagation();
        ABC.confirmAction("이 프로젝트를 삭제할까요?<br />소스·검수 기록이 함께 사라집니다.", async () => {
          try {
            await fetch(`/api/projects/${del.dataset.del}`, { method: "DELETE" });
          } catch {
            ABC.toast("삭제에 실패했습니다");
          }
          ABC.toast("프로젝트를 삭제했습니다");
          loadGallery();
        });
        return;
      }
      if (e.target.closest('[data-role="new"]')) {
        const res = await askInput("새 프로젝트", [
          { html: `<label class="field">이름<input type="text" data-name="name" placeholder="예: CCTV 이상행동 검색" /></label>` },
          {
            html:
              `<label class="field">아이콘<select data-name="emoji">` +
              EMOJIS.map((em) => `<option value="${em}">${em}</option>`).join("") +
              `</select></label>`,
          },
        ]);
        if (res && res.name) {
          const p = await ABC.api("/api/projects", { name: res.name, emoji: res.emoji || "📁" });
          ABC.toast("프로젝트를 만들었습니다");
          openProject(p.id);
        }
        return;
      }
      const manage = e.target.closest("[data-manage]");
      if (manage) {
        e.stopPropagation();
        openProject(manage.dataset.manage);
        return;
      }
      const card = e.target.closest("[data-enter]");
      if (card) enterProject(card.dataset.enter);
    });

    $('[data-role="src-list"]').addEventListener("click", (e) => {
      const rv = e.target.closest("[data-review]");
      if (rv) setReview(rv.dataset.review, rv.dataset.status);
    });

    $('[data-role="add-src"]').addEventListener("click", async () => {
      if (!currentPid) return;
      const res = await askInput("소스 추가", [
        { html: `<label class="field">소스 이름<input type="text" data-name="name" placeholder="예: 2026Q3 포트홀 이미지셋" /></label>` },
        {
          html:
            `<label class="field">유형<select data-name="kind">` +
            ["이미지셋", "문서", "공공데이터", "보고서"].map((k) => `<option>${k}</option>`).join("") +
            `</select></label>`,
        },
      ]);
      if (res && res.name) {
        const p = await ABC.api(`/api/projects/${currentPid}/sources`, { name: res.name, kind: res.kind });
        if (!p.error) {
          ABC.toast("소스를 추가했습니다 (검수 대기)");
          renderDetail(p);
        }
      }
    });

    // 딥링크: ?p=<id> 면 상세, 아니면 갤러리.
    const pid = new URLSearchParams(location.search).get("p");
    if (pid) openProject(pid);
    else loadGallery();
  });
})();
