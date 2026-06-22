document.addEventListener("DOMContentLoaded", () => {
  const askInput = document.querySelector(".ask-line input");
  const askButton = document.querySelector(".ask-line .primary");
  const answer = document.querySelector(".answer p");
  const confidence = document.querySelector(".answer-head .status:last-child");
  const methodTag = document.querySelector(".answer-head .status:first-child");
  const meta = document.querySelector(".answer-actions small");
  const sourceList = document.querySelector(".source-list");
  const sectionTitle = document.querySelector(".section-title small");

  const renderSources = (sources) => {
    if (!sourceList) return;
    sourceList.innerHTML = sources
      .map((src, i) => {
        const pct = Math.round(src.score * 100);
        return `<article class="card source"><div><b><span>${i + 1}</span>${ABC.escapeHtml(src.source)}</b><p>${ABC.escapeHtml(src.text)}</p></div><i><span style="width:${pct}%"></span></i><em>${src.score.toFixed(2)}</em></article>`;
      })
      .join("");
    if (sectionTitle) sectionTitle.textContent = `${sources.length} sources · RRF`;
  };

  const search = async () => {
    const query = askInput.value.trim();
    if (!query) {
      ABC.toast("질문을 입력해주세요");
      return;
    }
    const done = ABC.setBusy(askButton, "검색 중");
    try {
      const result = await ABC.api("/api/rag/search", { query });
      answer.innerHTML = result.answer;
      confidence.textContent = `신뢰도 ${result.confidence.toFixed(2)}`;
      if (methodTag) methodTag.textContent = result.method;
      if (meta) meta.textContent = `top-K ${result.top_k} · ${result.chunks} chunks · ${result.elapsed}`;
      renderSources(result.sources);
      ABC.toast("검색 결과가 갱신되었습니다");
    } catch {
      /* api()가 이미 toast 표시 */
    } finally {
      done();
    }
  };

  document.querySelectorAll(".chips .pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      ABC.activateInGroup(pill, ".pill");
      askInput.value = pill.textContent.trim();
    });
  });

  askButton?.addEventListener("click", search);
  askInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") search();
  });

  document.querySelector(".switch")?.addEventListener("click", (event) =>
    event.currentTarget.classList.toggle("off"),
  );

  document.querySelector(".index-actions .primary")?.addEventListener("click", async (event) => {
    const done = ABC.setBusy(event.currentTarget, "색인 중");
    try {
      const useSamples = !document.querySelector(".toggle-row .switch")?.classList.contains("off");
      const result = await ABC.api("/api/rag/index", { use_samples: useSamples });
      document.querySelector(".indexed").textContent = `✓ ${result.message}`;
      ABC.toast("문서 색인이 완료되었습니다");
    } catch {
      /* handled */
    } finally {
      done();
    }
  });

  const uploadInput = document.querySelector(".upload-input");
  const uploadBox = document.querySelector(".upload");
  const fileList = document.querySelector(".file-list");

  uploadInput?.addEventListener("change", () => {
    const files = [...uploadInput.files];
    if (!files.length) return;

    uploadBox.querySelector("b").textContent = `${files.length}개 문서 선택됨`;
    uploadBox.querySelector("small").textContent = files.map((file) => file.name).join(" · ");

    files.forEach((file) => {
      const item = document.createElement("li");
      item.innerHTML = `<i>▤</i><b>${ABC.escapeHtml(file.name)}</b><small>업로드 대기</small>`;
      fileList.prepend(item);
    });

    ABC.toast("문서가 업로드 목록에 추가되었습니다");
  });
});
