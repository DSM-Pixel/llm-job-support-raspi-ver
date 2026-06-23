document.addEventListener("DOMContentLoaded", () => {
  const input = document.querySelector(".input-wrap input");
  const sendButton = document.querySelector(".input-wrap button");
  const stage = document.querySelector(".query-stage");

  const ensureChat = () => {
    let log = stage.querySelector(".chat-log");
    if (log) return log;

    stage.classList.add("chat-mode");
    stage.innerHTML = `
      <div class="chat-log" aria-live="polite">
        <div class="message assistant">
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

  // AI 대화 패널 등에서 ?q=로 넘어온 일반 질문을 진입 시 바로 질의.
  const incomingQ = new URLSearchParams(location.search).get("q");
  if (incomingQ && input) {
    input.value = incomingQ;
    submit();
  }
});
