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

  // 서버 응답(paragraphs/steps/actions)을 답변 HTML로 조립.
  const renderAnswer = (data) => {
    const parts = (data.paragraphs || []).map((p) => `<p>${p}</p>`);
    if (data.steps && data.steps.length) {
      parts.push(`<ol>${data.steps.map((s) => `<li>${s}</li>`).join("")}</ol>`);
    }
    if (data.actions && data.actions.length) {
      const buttons = data.actions
        .map((a) => `<a class="btn${a.primary ? " primary" : ""}" href="${a.href}">${ABC.escapeHtml(a.label)}</a>`)
        .join("");
      parts.push(`<div class="message-actions">${buttons}</div>`);
    }
    return parts.join("");
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
});
