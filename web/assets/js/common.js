const ABC = (() => {
  // ── 설정 (localStorage 영속) ──────────────────────────────────────
  const SETTINGS_KEY = "gnsoft.settings";
  const DEFAULT_SETTINGS = {
    engine: "Gemini",
    name: "김연우",
    team: "R&D · 청년 1팀",
    notify: true,
  };

  const loadSettings = () => {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") };
    } catch {
      return { ...DEFAULT_SETTINGS };
    }
  };

  let settings = loadSettings();
  const getSettings = () => ({ ...settings });
  const saveSettings = (next) => {
    settings = { ...settings, ...next };
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch {
      /* localStorage 불가 시 무시 */
    }
  };

  const toast = (message) => {
    if (settings.notify === false) return; // 알림 끄기 설정 존중
    let el = document.querySelector(".toast");
    if (!el) {
      el = document.createElement("div");
      el.className = "toast";
      document.body.appendChild(el);
    }

    el.textContent = message;
    el.classList.add("show");
    window.clearTimeout(el.timer);
    el.timer = window.setTimeout(() => el.classList.remove("show"), 1800);
  };

  const setBusy = (button, text = "처리 중") => {
    if (!button) return () => {};
    const original = button.textContent;
    button.disabled = true;
    button.classList.add("is-loading");
    button.textContent = text;

    return () => {
      button.disabled = false;
      button.classList.remove("is-loading");
      button.textContent = original;
    };
  };

  // ── 활동 로그 (보고서 통계용, localStorage 영속) ────────────────
  // 사용자가 웹에서 한 행동(질의·검색·이미지 분석·라벨 저장·업로드 등)을
  // {ts, page, type, label} 형태로 누적. 보고서가 이를 분석·통계 낸다.
  const ACTIVITY_KEY = "gnsoft.activity";
  const logActivity = (type, label = "") => {
    try {
      const page = (location.pathname.split("/").pop() || "").replace(".html", "");
      const list = JSON.parse(localStorage.getItem(ACTIVITY_KEY) || "[]");
      list.push({ ts: Date.now(), page, type, label: String(label).slice(0, 200) });
      localStorage.setItem(ACTIVITY_KEY, JSON.stringify(list.slice(-300))); // 최근 300개 유지
    } catch {
      /* localStorage 불가 시 무시 */
    }
  };
  const getActivity = () => {
    try {
      return JSON.parse(localStorage.getItem(ACTIVITY_KEY) || "[]");
    } catch {
      return [];
    }
  };

  // ── 작업 산출물(아티팩트) 저장 — 보고서에 넣을 '내 작업 결과' ──────
  // 분석·라벨한 이미지(+라벨 결과)나 RAG로 도출한 결과(질문·근거파일·답)를
  // 저장해 두면, 보고서 페이지에서 골라 본문에 삽입할 수 있다.
  const ARTIFACT_KEY = "gnsoft.artifacts";

  // 이미지를 캔버스로 축소한 JPEG data URL로 변환(localStorage 용량 절약).
  const toThumb = (imgOrSrc, max = 560) =>
    new Promise((resolve) => {
      const draw = (el) => {
        const w = el.naturalWidth || el.width;
        const h = el.naturalHeight || el.height;
        if (!w || !h) return resolve("");
        const scale = Math.min(1, max / Math.max(w, h));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(w * scale);
        canvas.height = Math.round(h * scale);
        try {
          canvas.getContext("2d").drawImage(el, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL("image/jpeg", 0.72));
        } catch {
          resolve(""); // CORS 등으로 캔버스 오염 시 생략
        }
      };
      if (imgOrSrc instanceof HTMLImageElement && imgOrSrc.complete && imgOrSrc.naturalWidth) {
        draw(imgOrSrc);
      } else {
        const el = new Image();
        el.onload = () => draw(el);
        el.onerror = () => resolve("");
        el.src = imgOrSrc instanceof HTMLImageElement ? imgOrSrc.src : imgOrSrc;
      }
    });

  const saveArtifact = (art) => {
    const page = (location.pathname.split("/").pop() || "").replace(".html", "");
    const entry = { ts: Date.now(), page, ...art };
    try {
      let list = JSON.parse(localStorage.getItem(ARTIFACT_KEY) || "[]");
      list.push(entry);
      list = list.slice(-24); // 최근 24개 유지
      // 용량 초과 시 가장 오래된 이미지 아티팩트부터 제거하며 재시도.
      for (let i = 0; i < 10; i++) {
        try {
          localStorage.setItem(ARTIFACT_KEY, JSON.stringify(list));
          return;
        } catch {
          const idx = list.findIndex((a) => a.image);
          list.splice(idx >= 0 ? idx : 0, 1);
          if (!list.length) return;
        }
      }
    } catch {
      /* 무시 */
    }
  };

  const getArtifacts = () => {
    try {
      return JSON.parse(localStorage.getItem(ARTIFACT_KEY) || "[]");
    } catch {
      return [];
    }
  };

  const activateInGroup = (target, selector) => {
    const group = target.parentElement;
    if (!group) return;
    group.querySelectorAll(selector).forEach((item) => item.classList.remove("active"));
    target.classList.add("active");
  };

  // 백엔드 API 호출 헬퍼. GET: api(path) / POST: api(path, bodyObject).
  const api = async (path, body) => {
    const options = body
      ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
      : { method: "GET" };
    try {
      const response = await fetch(path, options);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      toast("서버 연결에 실패했습니다");
      throw error;
    }
  };

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  // (이전엔 아무 버튼이나 누르면 "~ 완료" 토스트를 띄웠으나, 실제 동작이 없는
  //  버튼도 완료된 것처럼 보여 오해를 주므로 제거했다. 각 핸들러가 직접 토스트한다.)

  // ── 설정 모달 (모든 페이지 사이드바의 ⚙) ────────────────────────
  const buildSettingsModal = () => {
    if (document.querySelector("#settings-modal")) return document.querySelector("#settings-modal");
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.id = "settings-modal";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true" aria-label="설정">
        <header class="modal-head">
          <h3>⚙ 설정</h3>
          <button class="modal-close" type="button" aria-label="닫기">✕</button>
        </header>
        <div class="modal-body">
          <div class="modal-form">
            <label class="field">탐지 엔진 (모델)
              <select name="engine">
                <option value="Gemini">Gemini (VLM)</option>
                <option value="YOLO-World">YOLO-World</option>
              </select>
            </label>
            <label class="field">이름
              <input type="text" name="name" placeholder="이름" />
            </label>
            <label class="field">직함 · 소속
              <input type="text" name="team" placeholder="예: R&D · 청년 1팀" />
            </label>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn modal-cancel" type="button">취소</button>
          <button class="btn primary modal-save-settings" type="button">저장</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    const close = () => {
      overlay.hidden = true;
    };
    overlay._fill = () => {
      overlay.querySelector("[name=engine]").value = settings.engine;
      overlay.querySelector("[name=name]").value = settings.name || "";
      overlay.querySelector("[name=team]").value = settings.team || "";
    };

    overlay.querySelector(".modal-close").addEventListener("click", close);
    overlay.querySelector(".modal-cancel").addEventListener("click", close);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close();
    });
    overlay.querySelector(".modal-save-settings").addEventListener("click", () => {
      saveSettings({
        engine: overlay.querySelector("[name=engine]").value,
        name: overlay.querySelector("[name=name]").value.trim() || "사용자",
        team: overlay.querySelector("[name=team]").value.trim(),
      });
      applyProfile();
      close();
      toast("설정을 저장했습니다");
    });
    return overlay;
  };

  // 설정의 이름/소속을 사이드바 프로필에 반영.
  const applyProfile = () => {
    const nameEl = document.querySelector(".user-name");
    const teamEl = document.querySelector(".user-team");
    const avatar = document.querySelector(".user-box .avatar");
    if (nameEl) nameEl.textContent = settings.name || "사용자";
    if (teamEl) teamEl.textContent = settings.team || "";
    if (avatar) avatar.textContent = (settings.name || "사용자").slice(0, 2);
  };

  const openSettings = () => {
    const overlay = buildSettingsModal();
    overlay._fill();
    overlay.hidden = false;
  };

  document.addEventListener("DOMContentLoaded", () => {
    applyProfile(); // 저장된 이름/소속을 사이드바에 반영
    document.querySelectorAll(".gear").forEach((gear) => {
      gear.style.cursor = "pointer";
      gear.setAttribute("role", "button");
      gear.setAttribute("tabindex", "0");
      gear.addEventListener("click", openSettings);
      gear.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openSettings();
        }
      });
    });
    document.addEventListener("keydown", (e) => {
      const modal = document.querySelector("#settings-modal");
      if (e.key === "Escape" && modal && !modal.hidden) modal.hidden = true;
    });

    // 상단 ?/♧ 정리: 클로바(♧) 제거, ?는 사용법 모달로.
    document.querySelectorAll(".top-actions span").forEach((s) => {
      const t = s.textContent.trim();
      if (t === "♧" || t === "♣") {
        s.remove();
      } else if (t === "?") {
        s.classList.add("help-trigger");
        s.title = "사용법 보기";
        s.style.cursor = "pointer";
        s.setAttribute("role", "button");
        s.addEventListener("click", () => openHelp());
      }
    });
  });

  // ── 사용법 모달 (화살표로 페이지별 안내) ────────────────────────
  const HELP_SLIDES = [
    {
      key: "dashboard",
      title: "STEP 1 · 메인 대시보드",
      body: [
        "여기서 시작합니다. 오늘의 운영 현황(색인 문서·라벨·모델 정확도·처리량)을 한눈에 봅니다.",
        "‘빠른 작업’ 카드를 누르면 원하는 작업 화면으로 바로 이동합니다.",
        "왼쪽 사이드바의 메뉴로 각 기능을, 맨 아래 ‘AI와 대화하기’로 AI 어시스턴트를 엽니다.",
      ],
    },
    {
      key: "query",
      title: "STEP 2 · 자연어 질의",
      body: [
        "‘포트홀이 뭐야?’처럼 일반적인 질문은 바로 답해 줍니다.",
        "날짜·위치로 특정 기록을 찾거나(예: 2026.04.24 8시 포트홀 위치) 이미지를 분석해야 하는 질문은, 데이터가 필요하다는 안내와 함께 RAG 공공데이터 검색·이미지 분석 화면으로 연결해 줍니다.",
      ],
    },
    {
      key: "rag",
      title: "STEP 3 · RAG 공공데이터 검색",
      body: [
        "① 왼쪽 ‘문서 준비’에서 문서를 선택하고 ‘문서 색인’을 눌러 참고 문서를 추가합니다.",
        "② 질문하면 색인 문서를 근거로 답하고, 아래에 근거 파일·내용을 보여줍니다.",
        "③ 참고 파일을 클릭하면 내용 열람, ✕로 삭제할 수 있습니다.",
      ],
    },
    {
      key: "labeling",
      title: "STEP 4 · 이미지 분석·라벨링",
      body: [
        "① ‘교체’로 이미지를 올립니다.",
        "② ‘분석하기’로 설명 분석, ‘크게 열어 라벨링’으로 박스 라벨링(드래그·AI 자동 탐지·삭제·편집).",
        "③ COCO/YOLO 내보내기·저장. ‘AI와 대화하기’로 그 이미지에 대해 질문할 수 있습니다.",
      ],
    },
    {
      key: "report",
      title: "STEP 5 · 요약·보고서 생성",
      body: [
        "① 보고서 유형·데이터 소스·기간·통계차트 포함을 고릅니다.",
        "② ‘보고서 생성’을 누르면 AI(웹 검색)가 문서를 작성해 미리보기에 띄웁니다.",
        "③ 본문을 클릭해 직접 수정. ‘AI와 대화하기’로 보고서 내용을 질문할 수 있습니다.",
      ],
    },
    {
      key: "data",
      title: "STEP 6 · 데이터 관리",
      body: [
        "데이터셋을 검색·필터하고, ‘업로드’로 파일을 추가(표에 행으로 표시)합니다.",
        "각 행의 ⋮ 메뉴에서 미리보기·이름 수정·삭제를 할 수 있습니다.",
      ],
    },
  ];

  let helpModal = null;
  let helpIndex = 0;

  const buildHelpModal = () => {
    if (helpModal) return helpModal;
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.id = "help-modal";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="modal help-modal" role="dialog" aria-modal="true" aria-label="사용법">
        <header class="modal-head"><h3>사용법 안내</h3>
          <button class="modal-close" type="button" aria-label="닫기">✕</button></header>
        <div class="modal-body">
          <div class="help-slide">
            <div class="help-badge"></div>
            <h4 class="help-title"></h4>
            <ul class="help-list"></ul>
          </div>
        </div>
        <div class="modal-foot help-foot">
          <button class="btn help-prev" type="button">← 이전</button>
          <span class="help-dots"></span>
          <button class="btn primary help-next" type="button">다음 →</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    const close = () => {
      overlay.hidden = true;
    };
    overlay.querySelector(".modal-close").addEventListener("click", close);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close();
    });
    overlay.querySelector(".help-prev").addEventListener("click", () => {
      helpIndex = (helpIndex - 1 + HELP_SLIDES.length) % HELP_SLIDES.length;
      renderHelp();
    });
    overlay.querySelector(".help-next").addEventListener("click", () => {
      helpIndex = (helpIndex + 1) % HELP_SLIDES.length;
      renderHelp();
    });
    document.addEventListener("keydown", (e) => {
      if (overlay.hidden) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") overlay.querySelector(".help-next").click();
      if (e.key === "ArrowLeft") overlay.querySelector(".help-prev").click();
    });
    helpModal = overlay;
    return overlay;
  };

  const renderHelp = () => {
    const s = HELP_SLIDES[helpIndex];
    const m = helpModal;
    m.querySelector(".help-badge").textContent = `${helpIndex + 1} / ${HELP_SLIDES.length}`;
    m.querySelector(".help-title").textContent = s.title;
    m.querySelector(".help-list").innerHTML = s.body
      .map((b) => `<li>${escapeHtml(b)}</li>`)
      .join("");
    m.querySelector(".help-dots").innerHTML = HELP_SLIDES.map(
      (_, i) => `<i class="help-dot${i === helpIndex ? " on" : ""}"></i>`,
    ).join("");
  };

  const openHelp = () => {
    buildHelpModal();
    // 현재 페이지에 해당하는 슬라이드부터 시작.
    const path = (location.pathname.split("/").pop() || "").replace(".html", "");
    const idx = HELP_SLIDES.findIndex((s) => path.includes(s.key));
    helpIndex = idx >= 0 ? idx : 0;
    renderHelp();
    helpModal.hidden = false;
  };

  // ── AI 대화 패널 (오른쪽 슬라이드 바) ───────────────────────────
  // 페이지가 자신의 컨텍스트로 답하도록 핸들러를 등록할 수 있다.
  let askHandler = null;
  let askScope = "웹 검색 기반으로 무엇이든 물어보세요";
  const registerAskHandler = (fn, scopeLabel) => {
    askHandler = fn;
    if (scopeLabel) askScope = scopeLabel;
  };

  const renderRich = (text) => {
    const lines = String(text || "")
      .split(/\n+/)
      .map((l) => l.trim())
      .filter(Boolean);
    let html = "";
    let inList = false;
    for (const ln of lines) {
      if (/^[-*•]\s+/.test(ln)) {
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        html += `<li>${escapeHtml(ln.replace(/^[-*•]\s+/, ""))}</li>`;
      } else {
        if (inList) {
          html += "</ul>";
          inList = false;
        }
        html += `<p>${escapeHtml(ln)}</p>`;
      }
    }
    if (inList) html += "</ul>";
    return html || "<p></p>";
  };

  let aiPanel = null;
  const buildAiPanel = () => {
    if (aiPanel) return aiPanel;
    const panel = document.createElement("aside");
    panel.className = "ai-panel";
    panel.hidden = true;
    panel.innerHTML = `
      <header class="ai-panel-head">
        <span class="ai-panel-title"><span class="ai-ava">AI</span> 어시스턴트</span>
        <button class="ai-panel-close" type="button" aria-label="닫기">✕</button>
      </header>
      <p class="ai-panel-scope"></p>
      <div class="ai-chat-log"></div>
      <div class="ai-chat-input">
        <input type="text" placeholder="메시지를 입력하세요" />
        <button class="ai-send btn primary" type="button" aria-label="보내기">↑</button>
      </div>`;
    document.body.appendChild(panel);

    const log = panel.querySelector(".ai-chat-log");
    const input = panel.querySelector(".ai-chat-input input");

    const addBubble = (role, html) => {
      const el = document.createElement("div");
      el.className = `ai-msg ${role}`;
      el.innerHTML = role === "user" ? `<div class="ai-bubble">${html}</div>` : `<span class="ai-ava sm">AI</span><div class="ai-bubble">${html}</div>`;
      log.appendChild(el);
      log.scrollTop = log.scrollHeight;
      return el;
    };

    const send = async () => {
      const q = input.value.trim();
      if (!q) return;
      addBubble("user", escapeHtml(q));
      input.value = "";
      const typing = addBubble("assistant", '<div class="ai-typing"><span></span><span></span><span></span></div>');
      try {
        const ans = askHandler
          ? await askHandler(q)
          : (await api("/api/query", { question: q })).answer;
        typing.querySelector(".ai-bubble").innerHTML = renderRich(ans);
      } catch {
        typing.querySelector(".ai-bubble").innerHTML = "<p>답변을 가져오지 못했습니다. 잠시 후 다시 시도해주세요.</p>";
      } finally {
        log.scrollTop = log.scrollHeight;
      }
    };

    panel.querySelector(".ai-send").addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });
    panel.querySelector(".ai-panel-close").addEventListener("click", () => {
      panel.classList.remove("open");
      document.body.classList.remove("ai-pushed"); // 본문 밀기 해제
      window.setTimeout(() => {
        panel.hidden = true;
      }, 200);
    });
    aiPanel = panel;
    return panel;
  };

  const openAi = () => {
    const panel = buildAiPanel();
    panel.querySelector(".ai-panel-scope").textContent = askScope;
    if (!panel.querySelector(".ai-chat-log").children.length) {
      panel
        .querySelector(".ai-chat-log")
        .insertAdjacentHTML(
          "beforeend",
          '<div class="ai-msg assistant"><span class="ai-ava sm">AI</span><div class="ai-bubble"><p>안녕하세요! 무엇을 도와드릴까요?</p></div></div>',
        );
    }
    panel.hidden = false;
    requestAnimationFrame(() => {
      panel.classList.add("open");
      document.body.classList.add("ai-pushed"); // 본문을 왼쪽으로 밀어 나란히 표시
    });
    panel.querySelector(".ai-chat-input input").focus();
  };

  document.addEventListener("DOMContentLoaded", () => {
    // 사이드바 하단에 'AI와 대화하기' 버튼 추가.
    const sidebar = document.querySelector(".sidebar");
    const userBox = sidebar?.querySelector(".user-box");
    if (sidebar && !sidebar.querySelector(".ai-open")) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ai-open";
      btn.innerHTML = "✦ AI와 대화하기";
      btn.addEventListener("click", openAi);
      if (userBox) sidebar.insertBefore(btn, userBox);
      else sidebar.appendChild(btn);
    }
  });

  return {
    toast,
    setBusy,
    activateInGroup,
    api,
    escapeHtml,
    getSettings,
    saveSettings,
    openSettings,
    openHelp,
    registerAskHandler,
    openAi,
    logActivity,
    getActivity,
    toThumb,
    saveArtifact,
    getArtifacts,
  };
})();
