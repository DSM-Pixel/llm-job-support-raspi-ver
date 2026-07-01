const ABC = (() => {
  // ── 설정 (localStorage 영속) ──────────────────────────────────────
  const SETTINGS_KEY = "gnsoft.settings";
  const DEFAULT_SETTINGS = {
    engine: "Gemini",
    name: "박도현",
    team: "도로관리처 · 점검분석팀",
    notify: true,
    theme: "light",
  };

  const loadSettings = () => {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") };
    } catch {
      return { ...DEFAULT_SETTINGS };
    }
  };

  let settings = loadSettings();

  // ── 현재 프로젝트(노트북) 컨텍스트 ───────────────────────────────
  // 앱은 '현재 프로젝트' 아래에서 돈다. 기록·작업물·대화·RAG 문서가 프로젝트별로
  // 분리된다. 프로젝트 미선택 상태로 작업 화면에 오면 프로젝트 선택으로 보낸다.
  const PROJECT_KEY = "gnsoft.currentProject";
  const getProject = () => {
    try {
      return JSON.parse(localStorage.getItem(PROJECT_KEY) || "null");
    } catch {
      return null;
    }
  };
  const setProject = (p) => {
    try {
      localStorage.setItem(PROJECT_KEY, JSON.stringify(p));
    } catch {
      /* 무시 */
    }
  };
  const clearProject = () => localStorage.removeItem(PROJECT_KEY);
  const _pid = () => (getProject() || {}).id || "none";

  // 화면 테마(라이트/다크)를 <html data-theme>에 반영. 깜빡임 줄이려 즉시 적용.
  const applyTheme = () => {
    document.documentElement.setAttribute("data-theme", settings.theme === "dark" ? "dark" : "light");
  };
  applyTheme();
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
  const actKey = () => `gnsoft.activity.${_pid()}`;
  const logActivity = (type, label = "") => {
    try {
      const page = (location.pathname.split("/").pop() || "").replace(".html", "");
      const list = JSON.parse(localStorage.getItem(actKey()) || "[]");
      list.push({ ts: Date.now(), page, type, label: String(label).slice(0, 200) });
      localStorage.setItem(actKey(), JSON.stringify(list.slice(-300))); // 최근 300개 유지
    } catch {
      /* localStorage 불가 시 무시 */
    }
  };
  const getActivity = () => {
    try {
      return JSON.parse(localStorage.getItem(actKey()) || "[]");
    } catch {
      return [];
    }
  };

  // ── 작업 산출물(아티팩트) 저장 — 보고서에 넣을 '내 작업 결과' ──────
  // 분석·라벨한 이미지(+라벨 결과)나 RAG로 도출한 결과(질문·근거파일·답)를
  // 저장해 두면, 보고서 페이지에서 골라 본문에 삽입할 수 있다.
  const artKey = () => `gnsoft.artifacts.${_pid()}`;

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
      let list = JSON.parse(localStorage.getItem(artKey()) || "[]");
      // 같은 id(예: 같은 사진의 분석/라벨)는 최신 것으로 교체 — 원본+라벨 중복 방지.
      if (art.id) list = list.filter((a) => a.id !== art.id);
      list.push(entry);
      list = list.slice(-24); // 최근 24개 유지
      // 용량 초과 시 가장 오래된 이미지 아티팩트부터 제거하며 재시도.
      for (let i = 0; i < 10; i++) {
        try {
          localStorage.setItem(artKey(), JSON.stringify(list));
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
      return JSON.parse(localStorage.getItem(artKey()) || "[]");
    } catch {
      return [];
    }
  };

  // ts 목록에 해당하는 기록을 영구 삭제(기록 관리에서 사용).
  const removeRecords = (key, tsSet) => {
    try {
      const list = JSON.parse(localStorage.getItem(key) || "[]").filter((x) => !tsSet.has(x.ts));
      localStorage.setItem(key, JSON.stringify(list));
    } catch {
      /* 무시 */
    }
  };
  const deleteActivities = (tsArr) => removeRecords(actKey(), new Set(tsArr.map(Number)));
  const deleteArtifacts = (tsArr) => removeRecords(artKey(), new Set(tsArr.map(Number)));

  // 상대 시간(방금/N분 전/N시간 전/N일 전).
  const relTime = (ts) => {
    const s = Math.floor((Date.now() - ts) / 1000);
    if (s < 60) return "방금";
    const mi = Math.floor(s / 60);
    if (mi < 60) return `${mi}분 전`;
    const h = Math.floor(mi / 60);
    if (h < 24) return `${h}시간 전`;
    return `${Math.floor(h / 24)}일 전`;
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
            <label class="field">이미지 탐지 모델
              <select name="engine">
                <option value="Gemini">gemini-2.5-flash · 멀티모달 VLM</option>
                <option value="YOLO-World">yolo-world · 탐지 전용</option>
              </select>
              <small class="field-hint">자연어 질의·RAG·보고서는 항상 gemini-2.5-flash(LLM)를 사용합니다.</small>
            </label>
            <label class="field">이름
              <input type="text" name="name" placeholder="이름" />
            </label>
            <label class="field">직함 · 소속
              <input type="text" name="team" placeholder="예: 도로관리처 · 점검분석팀" />
            </label>
            <label class="field">화면 테마
              <select name="theme">
                <option value="light">라이트 모드</option>
                <option value="dark">다크 모드</option>
              </select>
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
      overlay.querySelector("[name=theme]").value = settings.theme || "light";
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
        theme: overlay.querySelector("[name=theme]").value,
      });
      applyProfile();
      applyModel(); // 바뀐 모델명을 화면 칩에 즉시 반영
      applyTheme(); // 테마 즉시 반영
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
    // 아바타 이니셜 = 이름의 뒷 2글자(예: 염세현 → 세현, 박도현 → 도현).
    if (avatar) avatar.textContent = (settings.name || "사용자").slice(-2);
    // 대시보드 인사말 등 이름을 쓰는 다른 위치도 갱신.
    document
      .querySelectorAll(".user-greet")
      .forEach((el) => (el.textContent = settings.name || "사용자"));
  };

  const openSettings = () => {
    const overlay = buildSettingsModal();
    overlay._fill();
    overlay.hidden = false;
  };

  // 설정의 모델을 화면 모델 칩에 반영. [data-model] 요소를 채운다.
  //  - data-model="vision": 이미지 탐지 모델(설정에서 선택, 멀티모달)
  //  - data-model="llm"   : 텍스트 LLM (자연어 질의·RAG·보고서는 항상 Gemini)
  // 칩을 누르면 설정이 열려 어디서든 모델을 바꿀 수 있다.
  const MODEL_LABEL = {
    Gemini: "gemini-2.5-flash",
    "YOLO-World": "yolo-world",
  };
  const applyModel = () => {
    document.querySelectorAll("[data-model]").forEach((el) => {
      const kind = el.getAttribute("data-model");
      const name =
        kind === "vision" ? MODEL_LABEL[settings.engine] || settings.engine : "gemini-2.5-flash";
      const suffix =
        kind === "vision" ? (settings.engine === "YOLO-World" ? " · 탐지" : " · 멀티모달") : "";
      el.textContent = `⚙ ${name}${suffix}`;
      el.title = "AI 모델 — 클릭해 설정에서 변경";
      el.style.cursor = "pointer";
      if (!el._modelBound) {
        el._modelBound = true;
        el.setAttribute("role", "button");
        el.addEventListener("click", openSettings);
      }
    });
  };

  // ── 데모 시드 — 처음 열었을 때 '사용 중인 느낌'이 나도록 활동·작업물 채움 ──
  // 한 번만(gnsoft.demoSeeded) 실행하고, 이미 활동 기록이 있으면 건드리지 않는다.
  // (검증/실사용에서 이미 데이터가 있으면 그대로 둠)
  const seedDemoIfEmpty = () => {
    try {
      if (!getProject()) return; // 프로젝트 선택 전에는 시드하지 않음
      // 데모 시드는 '처음 들어간 프로젝트'에만 1회. 새로 만든 프로젝트는 빈 상태로 시작.
      if (localStorage.getItem("gnsoft.demoSeeded")) return;
      localStorage.setItem("gnsoft.demoSeeded", "1");
      if (localStorage.getItem(actKey())) return; // 사용 흔적 있으면 유지
      const now = Date.now();
      const H = 3600000;
      const D = 86400000;
      const acts = [
        { ts: now - 4 * H, page: "query", type: "자연어 질의", label: "포트홀 보수 기한이 어떻게 돼?" },
        { ts: now - 6 * H, page: "rag", type: "RAG 검색", label: "심각한 포트홀 긴급 보수 기준" },
        { ts: now - D - 3 * H, page: "labeling", type: "이미지 분석", label: "도로 파손/포트홀 찾기" },
        { ts: now - D - 4 * H, page: "labeling", type: "라벨 저장", label: "road_2026Q2_0142.jpg (3개)" },
        { ts: now - D - 6 * H, page: "report", type: "보고서 생성", label: "활동 통계" },
        { ts: now - 2 * D - 2 * H, page: "rag", type: "RAG 검색", label: "거북등 균열 보수 공법" },
        { ts: now - 2 * D - 5 * H, page: "query", type: "자연어 질의", label: "가드레일 점검 주기" },
        { ts: now - 3 * D - 3 * H, page: "labeling", type: "전체 AI 라벨링", label: "12장 · 박스 27개" },
        { ts: now - 3 * D - 7 * H, page: "rag", type: "문서 색인", label: "도로_균열_점검.md" },
        { ts: now - 4 * D - 4 * H, page: "query", type: "자연어 질의", label: "우천 시 긴급 보수 공법" },
        { ts: now - 4 * D - 8 * H, page: "labeling", type: "이미지 분석", label: "이상 상황 탐지" },
        { ts: now - 6 * D - 5 * H, page: "data", type: "데이터 업로드", label: "pothole_set_2026Q2" },
      ];
      localStorage.setItem(actKey(), JSON.stringify(acts));
      const arts = [
        {
          ts: now - D - 4 * H,
          kind: "image",
          page: "labeling",
          title: "라벨링 · road_2026Q2_0142.jpg",
          image: "../assets/img/intro-2-labeling.png",
          caption: "라벨 3개 · 포트홀, 균열",
        },
        {
          ts: now - 6 * H,
          kind: "rag",
          page: "rag",
          title: "RAG · 심각한 포트홀 긴급 보수 기준",
          question: "심각한 포트홀은 며칠 안에 보수해야 해?",
          answer: "심각(상) 등급은 발견 즉시 24시간 이내 긴급 보수 대상입니다.",
          source: "포트홀_보수_기준.md",
          snippet: "심각(상) 등급은 발견 즉시 24시간 이내 긴급 보수.",
        },
      ];
      localStorage.setItem(artKey(), JSON.stringify(arts));
    } catch {
      /* localStorage 불가 시 무시 */
    }
  };
  seedDemoIfEmpty();

  document.addEventListener("DOMContentLoaded", () => {
    applyProfile(); // 저장된 이름/소속을 사이드바에 반영
    applyModel(); // 저장된 모델을 모델 칩에 반영(+클릭 시 설정 열기)
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
        <header class="modal-head"><h3>사용법 가이드</h3>
          <button class="modal-close" type="button" aria-label="닫기">✕</button></header>
        <div class="modal-body">
          <div class="help-slide">
            <figure class="help-shot"><img alt="화면 미리보기" /></figure>
            <div class="help-text">
              <div class="help-badge"></div>
              <h4 class="help-title"></h4>
              <ul class="help-list"></ul>
              <button class="btn primary help-go" type="button">이 화면으로 이동 →</button>
            </div>
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
    overlay.querySelector(".help-go").addEventListener("click", () => {
      const key = HELP_SLIDES[helpIndex].key;
      const cur = (location.pathname.split("/").pop() || "").replace(".html", "");
      if (key && key !== cur) location.href = `${key}.html`;
      else close(); // 이미 그 화면이면 닫기만
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
    m.querySelector(".help-badge").textContent = `STEP ${helpIndex + 1} / ${HELP_SLIDES.length}`;
    m.querySelector(".help-title").textContent = s.title;
    m.querySelector(".help-list").innerHTML = s.body
      .map((b) => `<li>${escapeHtml(b)}</li>`)
      .join("");
    const shot = m.querySelector(".help-shot img");
    shot.src = `../assets/img/guide/${s.key}.png`;
    shot.alt = `${s.title} 화면 미리보기`;
    // 현재 화면이면 '이 화면으로 이동' 대신 닫기 안내.
    const cur = (location.pathname.split("/").pop() || "").replace(".html", "");
    const go = m.querySelector(".help-go");
    go.textContent = s.key === cur ? "지금 이 화면이에요 · 닫기" : "이 화면으로 이동 →";
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

  // 대화 기록을 프로젝트·페이지별로 영속(닫았다 켜도 유지, '지우기'로만 비움).
  const chatKey = () =>
    `gnsoft.chat.${_pid()}.${(location.pathname.split("/").pop() || "").replace(".html", "") || "page"}`;

  // 화면 컨텍스트와 무관한 '일반 지식' 질문인지 — 자연어 질의로 보낼지 판단.
  // 화면을 가리키는 말(이 보고서/이미지/여기/요약/섹션 등)이 있으면 컨텍스트 질문으로 본다.
  const RE_PAGEREF =
    /이\s*(보고서|문서|이미지|사진|화면|내용|자료|표)|여기|위\s*내용|방금|이거|이걸|요약|핵심|서론|본론|결론|섹션|문단|출처/;
  const RE_GENERALQ = /뭐야|뭐임|무엇|무어|이란|란\s*뭐|왜냐|왜\s|어떻게|방법|종류|원인|차이|날씨|예방|정의|개념|의미/;
  const looksGeneral = (q) => RE_GENERALQ.test(q) && !RE_PAGEREF.test(q);

  const GREETING =
    '<div class="ai-msg assistant"><span class="ai-ava sm">AI</span><div class="ai-bubble"><p>안녕하세요! 지금 화면 내용에 대해 무엇이든 물어보세요.</p></div></div>';

  let aiPanel = null;
  const buildAiPanel = () => {
    if (aiPanel) return aiPanel;
    const panel = document.createElement("aside");
    panel.className = "ai-panel";
    panel.hidden = true;
    panel.innerHTML = `
      <header class="ai-panel-head">
        <span class="ai-panel-title"><span class="ai-ava">AI</span> 어시스턴트</span>
        <div class="ai-panel-actions">
          <button class="ai-panel-clear" type="button">지우기</button>
          <button class="ai-panel-close" type="button" aria-label="닫기">✕</button>
        </div>
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

    // 저장된 대화 복원(없으면 빈 상태).
    try {
      const saved = localStorage.getItem(chatKey());
      if (saved) log.innerHTML = saved;
    } catch {
      /* 무시 */
    }
    const saveChat = () => {
      try {
        localStorage.setItem(chatKey(), log.innerHTML);
      } catch {
        /* 무시 */
      }
    };

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
      // 컨텍스트 패널(askHandler 등록됨)인데 화면과 무관한 일반 질문이면 자연어 질의로 안내.
      if (askHandler && looksGeneral(q)) {
        addBubble(
          "assistant",
          renderRich(
            `이 대화는 지금 화면 내용에 대한 질문에 답해요. ‘${q}’ 같은 일반 질문은 ‘자연어 질의’에서 답해드릴게요.`,
          ) +
            `<a class="btn primary ai-route" href="query.html?q=${encodeURIComponent(q)}">자연어 질의로 물어보기 →</a>`,
        );
        saveChat();
        return;
      }
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
        saveChat();
      }
    };

    // '지우기' → 대화 비우고 인사말만 남김(이때만 기록이 바뀐다).
    panel.querySelector(".ai-panel-clear").addEventListener("click", () => {
      log.innerHTML = GREETING;
      saveChat();
    });

    panel.querySelector(".ai-send").addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });
    panel.querySelector(".ai-panel-close").addEventListener("click", closeAi);
    aiPanel = panel;
    return panel;
  };

  // 패널 닫기(본문 밀기 해제 + 슬라이드 아웃).
  const closeAi = () => {
    if (!aiPanel) return;
    aiPanel.classList.remove("open");
    document.body.classList.remove("ai-pushed");
    document.querySelector(".ai-open")?.classList.remove("is-on");
    window.setTimeout(() => {
      if (aiPanel) aiPanel.hidden = true;
    }, 200);
  };

  const isAiOpen = () => !!aiPanel && !aiPanel.hidden && aiPanel.classList.contains("open");

  // 'AI와 대화하기' 버튼 = 열려 있으면 닫고, 닫혀 있으면 연다(토글).
  const toggleAi = () => {
    if (isAiOpen()) closeAi();
    else openAi();
  };

  const openAi = () => {
    const panel = buildAiPanel();
    panel.querySelector(".ai-panel-scope").textContent = askScope;
    // 저장된 대화가 없을 때만 인사말 표시(있으면 이전 대화 그대로 유지).
    if (!panel.querySelector(".ai-chat-log").children.length) {
      panel.querySelector(".ai-chat-log").insertAdjacentHTML("beforeend", GREETING);
    }
    panel.hidden = false;
    requestAnimationFrame(() => {
      panel.classList.add("open");
      document.body.classList.add("ai-pushed"); // 본문을 왼쪽으로 밀어 나란히 표시
    });
    document.querySelector(".ai-open")?.classList.add("is-on");
    panel.querySelector(".ai-chat-input input").focus();
  };

  // 되돌릴 수 없는 작업 확인 모달(영구 삭제 등) — 공용.
  let confirmModal = null;
  const confirmAction = (messageHtml, onConfirm) => {
    if (!confirmModal) {
      confirmModal = document.createElement("div");
      confirmModal.className = "modal-overlay confirm-overlay";
      confirmModal.hidden = true;
      confirmModal.innerHTML =
        '<div class="modal confirm-modal"><header class="modal-head"><h3>영구 삭제</h3>' +
        '<button class="modal-close" type="button" aria-label="닫기">✕</button></header>' +
        '<div class="modal-body"><p class="confirm-text"></p></div>' +
        '<div class="modal-foot"><button class="btn modal-cancel" type="button">취소</button>' +
        '<button class="btn danger confirm-ok" type="button">삭제</button></div></div>';
      document.body.appendChild(confirmModal);
      const close = () => {
        confirmModal.hidden = true;
      };
      confirmModal.querySelector(".modal-close").addEventListener("click", close);
      confirmModal.querySelector(".modal-cancel").addEventListener("click", close);
      confirmModal.addEventListener("click", (e) => {
        if (e.target === confirmModal) close();
      });
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && confirmModal && !confirmModal.hidden) close();
      });
    }
    confirmModal.querySelector(".confirm-text").innerHTML = messageHtml;
    // 이전 클릭 핸들러 제거를 위해 버튼을 교체.
    const old = confirmModal.querySelector(".confirm-ok");
    const fresh = old.cloneNode(true);
    old.replaceWith(fresh);
    fresh.addEventListener("click", () => {
      confirmModal.hidden = true;
      onConfirm();
    });
    confirmModal.hidden = false;
  };

  // ── 기록 관리 모달 — 실제 활동·작업 기록(localStorage)을 나열·영구삭제 ──
  const HIST_ICON = {
    "자연어 질의": "☰",
    "RAG 검색": "⌕",
    "문서 색인": "▱",
    "이미지 분석": "⌗",
    "라벨 저장": "⌗",
    "데이터 업로드": "▱",
  };
  let historyModal = null;

  // 사진 크게 보기(라이트박스) — 기록 관리의 썸네일 클릭 시.
  let lightbox = null;
  const openLightbox = (src) => {
    if (!src) return;
    if (!lightbox) {
      lightbox = document.createElement("div");
      lightbox.className = "modal-overlay lightbox-overlay";
      lightbox.hidden = true;
      lightbox.innerHTML = '<img class="lightbox-img" alt="" />';
      document.body.appendChild(lightbox);
      lightbox.addEventListener("click", () => {
        lightbox.hidden = true;
      });
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && lightbox && !lightbox.hidden) lightbox.hidden = true;
      });
    }
    lightbox.querySelector(".lightbox-img").src = src;
    lightbox.hidden = false;
  };

  const buildHistoryModal = () => {
    if (historyModal) return historyModal;
    const m = document.createElement("div");
    m.className = "modal-overlay history-overlay";
    m.hidden = true;
    m.innerHTML =
      '<div class="modal history-modal"><header class="modal-head"><h3>기록 관리</h3>' +
      '<button class="modal-close" type="button" aria-label="닫기">✕</button></header>' +
      '<div class="history-toolbar"><label class="hist-all"><input type="checkbox" class="hist-select-all" /><span>전체 선택</span></label>' +
      '<span class="hist-count">선택 0개</span>' +
      '<button class="btn danger hist-delete" type="button" disabled>선택 삭제</button></div>' +
      '<div class="modal-body"><ul class="history-list"></ul></div></div>';
    document.body.appendChild(m);

    const listEl = m.querySelector(".history-list");
    const selAll = m.querySelector(".hist-select-all");
    const delBtn = m.querySelector(".hist-delete");
    const countEl = m.querySelector(".hist-count");
    const refresh = () => {
      const cbs = [...listEl.querySelectorAll(".hist-cb")];
      const checked = cbs.filter((c) => c.checked);
      countEl.textContent = `선택 ${checked.length}개`;
      delBtn.disabled = checked.length === 0;
      selAll.checked = cbs.length > 0 && checked.length === cbs.length;
    };
    const close = () => {
      m.hidden = true;
    };
    m.querySelector(".modal-close").addEventListener("click", close);
    m.addEventListener("click", (e) => {
      if (e.target === m) close();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && historyModal && !historyModal.hidden) close();
    });
    listEl.addEventListener("change", refresh);
    // 클릭: 썸네일이면 크게 보기, 그 외(체크박스 제외)는 행 체크 토글.
    listEl.addEventListener("click", (e) => {
      const thumb = e.target.closest(".hist-thumb");
      if (thumb) {
        openLightbox(thumb.src);
        return;
      }
      if (e.target.closest("input")) return;
      const cb = e.target.closest(".hist-row")?.querySelector(".hist-cb");
      if (cb) {
        cb.checked = !cb.checked;
        refresh();
      }
    });
    selAll.addEventListener("change", () => {
      listEl.querySelectorAll(".hist-cb").forEach((c) => {
        c.checked = selAll.checked;
      });
      refresh();
    });
    delBtn.addEventListener("click", () => {
      const keys = [...listEl.querySelectorAll(".hist-cb:checked")].map((c) => c.dataset.key);
      if (!keys.length) return;
      confirmAction(
        `선택한 기록 ${keys.length}개를 영구 삭제할까요?<br />이 작업은 되돌릴 수 없습니다.`,
        () => {
          const actTs = [];
          const artTs = [];
          keys.forEach((k) => {
            const [kind, ts] = k.split(":");
            (kind === "act" ? actTs : artTs).push(ts);
          });
          if (actTs.length) deleteActivities(actTs);
          if (artTs.length) deleteArtifacts(artTs);
          toast(`기록 ${keys.length}개를 삭제했습니다`);
          renderHistory();
        },
      );
    });
    historyModal = m;
    return m;
  };

  const renderHistory = () => {
    const m = buildHistoryModal();
    const listEl = m.querySelector(".history-list");
    const acts = getActivity().map((a) => ({
      kind: "act",
      ts: a.ts,
      page: a.page,
      cat: a.type,
      title: a.type + (a.label ? ` — ${a.label}` : ""),
      image: "",
    }));
    const arts = getArtifacts().map((a) => ({
      kind: "art",
      ts: a.ts,
      page: a.page,
      cat: a.kind === "rag" ? "RAG 결과" : "이미지 작업",
      title: a.title || a.question || a.caption || "작업 결과",
      image: a.image || "",
    }));
    const all = [...acts, ...arts].sort((x, y) => y.ts - x.ts);
    if (!all.length) {
      listEl.innerHTML =
        '<li class="hist-empty">아직 기록이 없습니다. 자연어 질의·RAG 검색·이미지 라벨링을 사용하면 여기에 쌓입니다.</li>';
    } else {
      listEl.innerHTML = all
        .map((r) => {
          const ic = HIST_ICON[r.cat] || (r.kind === "art" ? "◫" : "•");
          const thumb = r.image ? `<img class="hist-thumb" src="${r.image}" alt="" />` : "";
          return (
            `<li class="hist-row"><label class="hist-check"><input type="checkbox" class="hist-cb" data-key="${r.kind}:${r.ts}" /></label>` +
            `<span class="hist-ic">${ic}</span>` +
            `<div class="hist-info"><b>${escapeHtml(r.title)}</b><small>${escapeHtml(r.cat)} · ${escapeHtml(r.page || "")} · ${relTime(r.ts)}</small></div>` +
            thumb +
            `</li>`
          );
        })
        .join("");
    }
    m.querySelector(".hist-select-all").checked = false;
    m.querySelector(".hist-count").textContent = "선택 0개";
    m.querySelector(".hist-delete").disabled = true;
  };

  const openHistory = () => {
    renderHistory();
    buildHistoryModal().hidden = false;
  };

  // 작업 화면인지(프로젝트 필요) — 프로젝트 선택/랜딩 화면은 제외.
  const _page = () => (location.pathname.split("/").pop() || "").replace(".html", "");
  const _needsProject = () => !["projects", "index", ""].includes(_page());

  document.addEventListener("DOMContentLoaded", () => {
    // 프로젝트 미선택 상태로 작업 화면에 오면 프로젝트 선택 화면으로 보낸다.
    if (_needsProject() && !getProject()) {
      location.replace("projects.html");
      return;
    }

    const sidebar = document.querySelector(".sidebar");
    const userBox = sidebar?.querySelector(".user-box");

    // 사이드바 상단(로고 아래)에 현재 프로젝트 칩 — 클릭 시 프로젝트 전환.
    const proj = getProject();
    if (sidebar && proj && _needsProject() && !sidebar.querySelector(".project-switch")) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "project-switch";
      chip.title = "프로젝트 전환";
      chip.innerHTML =
        `<span class="ps-emoji">${escapeHtml(proj.emoji || "📁")}</span>` +
        `<span class="ps-name">${escapeHtml(proj.name || "프로젝트")}</span>` +
        `<span class="ps-swap">전환 ⇄</span>`;
      chip.addEventListener("click", () => (location.href = "projects.html"));
      const logo = sidebar.querySelector(".logo");
      if (logo) logo.insertAdjacentElement("afterend", chip);
      else sidebar.prepend(chip);
    }
    // 사이드바 하단에 'AI와 대화하기' 버튼 + 그 아래 '기록 관리' 링크 추가.
    // (프로젝트에 종속된 기능이므로 작업 화면에서만 — 프로젝트 선택 화면엔 없음)
    if (sidebar && _needsProject() && !sidebar.querySelector(".ai-open")) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ai-open";
      btn.innerHTML = "✦ AI와 대화하기";
      btn.addEventListener("click", toggleAi);
      if (userBox) sidebar.insertBefore(btn, userBox);
      else sidebar.appendChild(btn);
    }
    if (sidebar && _needsProject() && !sidebar.querySelector(".history-open")) {
      const hbtn = document.createElement("button");
      hbtn.type = "button";
      hbtn.className = "history-open";
      hbtn.textContent = "기록 관리";
      hbtn.title = "내 질의·검색·이미지 작업 기록을 보고 삭제";
      hbtn.addEventListener("click", openHistory);
      if (userBox) sidebar.insertBefore(hbtn, userBox);
      else sidebar.appendChild(hbtn);
    }
  });

  return {
    getProject,
    setProject,
    clearProject,
    toast,
    setBusy,
    activateInGroup,
    api,
    escapeHtml,
    getSettings,
    saveSettings,
    openSettings,
    applyModel,
    openHelp,
    registerAskHandler,
    openAi,
    logActivity,
    getActivity,
    toThumb,
    saveArtifact,
    getArtifacts,
    deleteActivities,
    deleteArtifacts,
    openHistory,
    confirmAction,
    relTime,
  };
})();
