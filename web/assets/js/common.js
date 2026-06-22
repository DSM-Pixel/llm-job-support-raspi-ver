const ABC = (() => {
  // ── 설정 (localStorage 영속) ──────────────────────────────────────
  const SETTINGS_KEY = "gnsoft.settings";
  const DEFAULT_SETTINGS = {
    engine: "Gemini",
    minConf: 0,
    defaultClass: "포트홀",
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
            <label class="field">탐지 엔진
              <select name="engine">
                <option value="Gemini">Gemini (VLM)</option>
                <option value="YOLO-World">YOLO-World</option>
              </select>
            </label>
            <label class="field">기본 신뢰도 임계값 <span class="set-conf-val"></span>
              <input type="range" name="minConf" min="0" max="100" step="5" />
            </label>
            <label class="field">기본 클래스명
              <input type="text" name="defaultClass" />
            </label>
            <label class="field row">토스트 알림 표시
              <input type="checkbox" name="notify" />
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
      overlay.querySelector("[name=minConf]").value = settings.minConf;
      overlay.querySelector("[name=defaultClass]").value = settings.defaultClass;
      overlay.querySelector("[name=notify]").checked = settings.notify !== false;
      overlay.querySelector(".set-conf-val").textContent = `${settings.minConf}%`;
    };

    overlay.querySelector("[name=minConf]").addEventListener("input", (e) => {
      overlay.querySelector(".set-conf-val").textContent = `${e.target.value}%`;
    });
    overlay.querySelector(".modal-close").addEventListener("click", close);
    overlay.querySelector(".modal-cancel").addEventListener("click", close);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close();
    });
    overlay.querySelector(".modal-save-settings").addEventListener("click", () => {
      saveSettings({
        engine: overlay.querySelector("[name=engine]").value,
        minConf: Number(overlay.querySelector("[name=minConf]").value) || 0,
        defaultClass: overlay.querySelector("[name=defaultClass]").value.trim() || "객체",
        notify: overlay.querySelector("[name=notify]").checked,
      });
      close();
      toast("설정을 저장했습니다");
    });
    return overlay;
  };

  const openSettings = () => {
    const overlay = buildSettingsModal();
    overlay._fill();
    overlay.hidden = false;
  };

  document.addEventListener("DOMContentLoaded", () => {
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
  });

  return { toast, setBusy, activateInGroup, api, escapeHtml, getSettings, saveSettings, openSettings };
})();
