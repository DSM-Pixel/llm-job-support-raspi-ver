document.addEventListener("DOMContentLoaded", () => {
  const input = document.querySelector(".input-wrap input");
  const sendButton = document.querySelector(".input-wrap button");
  const stage = document.querySelector(".query-stage");

  // 대화 기록 저장소(세션 단위). 탭을 옮겼다 와도 유지되고,
  // 새로고침(reload)이나 '새 대화'를 누를 때만 비운다.
  const CHAT_KEY = "gnsoft.query.chat";
  const navType = (() => {
    try {
      const nav = performance.getEntriesByType("navigation")[0];
      if (nav && nav.type) return nav.type; // navigate | reload | back_forward
    } catch {
      /* 구형 브라우저 폴백 */
    }
    return performance.navigation && performance.navigation.type === 1 ? "reload" : "navigate";
  })();

  const saveChat = () => {
    const log = stage.querySelector(".chat-log");
    if (!log) return;
    // 인사말(intro)·입력 중(typing)은 빼고 사용자/답변 메시지만 저장.
    const msgs = [...log.querySelectorAll(".message:not(.intro)")]
      .map((m) => ({
        role: m.classList.contains("user") ? "user" : "assistant",
        html: m.querySelector(".message-body")?.innerHTML || "",
      }))
      .filter((m) => m.html && !m.html.includes("class=\"typing\""));
    try {
      sessionStorage.setItem(CHAT_KEY, JSON.stringify(msgs));
    } catch {
      /* 저장 실패는 무시 */
    }
  };

  const ensureChat = () => {
    let log = stage.querySelector(".chat-log");
    if (log) return log;

    stage.classList.add("chat-mode");
    stage.innerHTML = `
      <div class="chat-toolbar">
        <button type="button" class="new-chat" title="대화를 비우고 새로 시작">＋ 새 대화</button>
      </div>
      <div class="chat-log" aria-live="polite">
        <div class="message assistant intro">
          <div class="message-avatar">AI</div>
          <div class="message-body">
            <p>안녕하세요. 도로 파손 분석, 공공데이터 검색, 보고서 생성, 이미지 라벨링 업무를 자연어로 도와드릴 수 있습니다.</p>
            <div class="message-tools">
              <button type="button" data-prompt="포트홀 영역을 찾아줘">이미지 분석</button>
              <button type="button" data-prompt="도로 파손 신고 현황을 요약해줘">데이터 요약</button>
              <button type="button" data-prompt="최근 3년 도로 파손 현황 보고서를 만들어줘">보고서 생성</button>
            </div>
          </div>
        </div>
      </div>`;

    log = stage.querySelector(".chat-log");
    log.querySelectorAll("[data-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.dataset.prompt;
        input.focus();
      });
    });
    // 새 대화: 저장된 기록을 비우고 인사말만 남긴다(그 자리에서 초기화).
    stage.querySelector(".new-chat")?.addEventListener("click", () => {
      try {
        sessionStorage.removeItem(CHAT_KEY);
      } catch {
        /* 무시 */
      }
      log.querySelectorAll(".message:not(.intro)").forEach((m) => m.remove());
      log.scrollTop = 0;
      input?.focus();
    });
    return log;
  };

  const addMessage = (role, html) => {
    const log = ensureChat();
    const message = document.createElement("div");
    message.className = `message ${role}`;
    message.innerHTML = `
      <div class="message-avatar">${role === "user" ? "김연" : "AI"}</div>
      <div class="message-body">${html}</div>`;
    log.appendChild(message);
    log.scrollTop = log.scrollHeight;
    return message;
  };

  // 답변 텍스트(여러 문단 + '- ' 불릿)를 HTML로.
  const renderText = (text) => {
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
        html += `<li>${ABC.escapeHtml(ln.replace(/^[-*•]\s+/, ""))}</li>`;
      } else {
        if (inList) {
          html += "</ul>";
          inList = false;
        }
        html += `<p>${ABC.escapeHtml(ln)}</p>`;
      }
    }
    if (inList) html += "</ul>";
    return html || "<p></p>";
  };

  // 서버 응답(answer/sources/actions)을 답변 HTML로 조립.
  const renderAnswer = (data) => {
    let html = renderText(data.answer);
    if (data.sources && data.sources.length) {
      const links = data.sources
        .map((s) =>
          s && typeof s === "object"
            ? `<a class="pill src-link" href="${s.url}" target="_blank" rel="noopener">${ABC.escapeHtml(s.title)}</a>`
            : `<span class="pill">${ABC.escapeHtml(s)}</span>`,
        )
        .join("");
      html += `<div class="msg-sources"><b>참고</b>${links}</div>`;
    }
    if (data.actions && data.actions.length) {
      const buttons = data.actions
        .map((a) => `<a class="btn${a.primary ? " primary" : ""}" href="${a.href}">${ABC.escapeHtml(a.label)}</a>`)
        .join("");
      html += `<div class="message-actions">${buttons}</div>`;
    }
    return html;
  };

  const submit = async () => {
    const question = input.value.trim();
    if (!question) {
      ABC.toast("질문을 입력해주세요");
      input.focus();
      return;
    }

    addMessage("user", `<p>${ABC.escapeHtml(question)}</p>`);
    input.value = "";
    saveChat();

    const done = ABC.setBusy(sendButton, "...");
    const typing = addMessage("assistant", `<div class="typing"><span></span><span></span><span></span></div>`);

    try {
      const data = await ABC.api("/api/query", { question });
      typing.querySelector(".message-body").innerHTML = renderAnswer(data);
      ABC.logActivity("자연어 질의", question);
    } catch {
      typing.querySelector(".message-body").innerHTML = "<p>답변을 가져오지 못했습니다. 잠시 후 다시 시도해주세요.</p>";
    } finally {
      typing.scrollIntoView({ behavior: "smooth", block: "end" });
      saveChat();
      done();
    }
  };

  document.querySelectorAll(".prompt-grid button, .suggestions .pill").forEach((item) => {
    item.addEventListener("click", () => {
      input.value = item.textContent.trim();
      input.focus();
    });
  });

  sendButton?.addEventListener("click", submit);
  input?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") submit();
  });

  // 새로고침이면 기록을 비우고(초기화), 그 외(탭 이동·뒤로가기)면 복원한다.
  if (navType === "reload") {
    try {
      sessionStorage.removeItem(CHAT_KEY);
    } catch {
      /* 무시 */
    }
  } else {
    try {
      const saved = JSON.parse(sessionStorage.getItem(CHAT_KEY) || "[]");
      if (Array.isArray(saved) && saved.length) {
        saved.forEach((m) => addMessage(m.role === "user" ? "user" : "assistant", m.html));
      }
    } catch {
      /* 손상된 기록 무시 */
    }
  }

  // AI 대화 패널 등에서 ?q=로 넘어온 일반 질문을 진입 시 바로 질의.
  const incomingQ = new URLSearchParams(location.search).get("q");
  if (incomingQ && input) {
    input.value = incomingQ;
    submit();
  }
});
