document.addEventListener("DOMContentLoaded", () => {
  const askInput = document.querySelector(".ask-line input");
  const askButton = document.querySelector(".ask-line .primary");
  const answer = document.querySelector(".answer p");
  const confidence = document.querySelector(".answer-head > .status");
  const methodTag = document.querySelector(".answer-head h3 .status");
  const meta = document.querySelector(".answer-actions small");
  const sourceList = document.querySelector(".source-list");
  const sectionTitle = document.querySelector(".section-title small");

  const renderSources = (sources) => {
    if (!sourceList) return;
    sourceList.innerHTML = sources
      .map((src, i) => {
        const pct = Math.max(0, Math.min(100, src.score)); // 질의 연관도 0~100
        return `<article class="card source"><div><b><span>${i + 1}</span>${ABC.escapeHtml(src.source)}</b><p>${ABC.escapeHtml(src.text)}</p></div><i><span style="width:${pct}%"></span></i><em title="이 문서가 질문과 얼마나 관련 있는지(연관도)">${pct}%</em></article>`;
      })
      .join("");
    if (sectionTitle) sectionTitle.textContent = `${sources.length}개 근거 · 연관도순`;
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
      confidence.textContent = result.found ? `연관도 ${result.confidence}%` : "근거 없음";
      if (methodTag) methodTag.textContent = result.method;
      if (meta) meta.textContent = `top-K ${result.top_k} · ${result.chunks} chunks · ${result.elapsed}`;
      renderSources(result.sources);
      ABC.toast(result.found ? "검색 결과가 갱신되었습니다" : "참고 문서에 관련 정보가 없습니다");
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

  // 색인 초기화
  document.querySelector(".index-actions .flat")?.addEventListener("click", async (event) => {
    const done = ABC.setBusy(event.currentTarget, "초기화 중");
    try {
      const result = await ABC.api("/api/rag/reset", {});
      document.querySelector(".indexed").textContent = `✓ ${result.message}`;
      ABC.toast("색인을 초기화했습니다");
    } catch {
      /* handled */
    } finally {
      done();
    }
  });

  const fileList = document.querySelector(".file-list");

  // 색인된 문서를 "참고중인 파일" 목록에 추가.
  const addToFileList = (name, sub) => {
    const item = document.createElement("li");
    item.innerHTML = `<i>▤</i><b>${ABC.escapeHtml(name)}</b><small>${ABC.escapeHtml(sub)}</small>`;
    fileList?.prepend(item);
  };

  // 웹에서 찾아 넣기 — 결과를 체크박스로 보여주고, 선택한 것만 색인에 추가.
  const webInput = document.querySelector(".search-line input");
  const webButton = document.querySelector(".search-line button");
  const webResults = document.querySelector(".web-results");

  const renderWebResults = (results) => {
    webResults.innerHTML =
      results
        .map(
          (r, i) =>
            `<label class="web-item"><input type="checkbox" data-i="${i}" checked /><div><b>${ABC.escapeHtml(r.title)}</b><small>${ABC.escapeHtml(r.url)}</small><p>${ABC.escapeHtml(r.snippet)}</p></div></label>`,
        )
        .join("") + `<button class="btn primary add-web" type="button">선택한 문서 색인에 추가</button>`;

    webResults.querySelector(".add-web")?.addEventListener("click", async (event) => {
      const picked = [...webResults.querySelectorAll("input:checked")].map(
        (cb) => results[Number(cb.dataset.i)],
      );
      if (!picked.length) {
        ABC.toast("추가할 문서를 선택하세요");
        return;
      }
      const done = ABC.setBusy(event.currentTarget, "추가 중");
      try {
        const docs = picked.map((r) => ({ name: r.title, text: r.snippet }));
        const res = await ABC.api("/api/rag/index", { docs, use_samples: true });
        picked.forEach((r) => addToFileList(r.title, r.url));
        document.querySelector(".indexed").textContent = `✓ ${res.message}`;
        webResults.innerHTML = "";
        ABC.toast(`${picked.length}개 문서를 색인에 추가했습니다`);
      } catch {
        /* handled */
      } finally {
        done();
      }
    });
  };

  webButton?.addEventListener("click", async () => {
    const keyword = webInput?.value.trim();
    if (!keyword) {
      ABC.toast("검색어를 입력해주세요");
      return;
    }
    const done = ABC.setBusy(webButton, "검색 중");
    try {
      const result = await ABC.api("/api/rag/web-search", { keyword });
      renderWebResults(result.results);
      ABC.toast(result.message);
    } catch {
      /* handled */
    } finally {
      done();
    }
  });

  // 답변 액션: "보고서로 생성" / "복사"
  document.querySelectorAll(".answer-actions button").forEach((button) => {
    const label = button.textContent.trim();
    if (label.includes("보고서")) {
      button.addEventListener("click", () => {
        window.location.href = "report.html";
      });
    } else if (label.includes("복사")) {
      button.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(answer.textContent.trim());
          ABC.toast("답변을 복사했습니다");
        } catch {
          ABC.toast("복사를 지원하지 않는 브라우저입니다");
        }
      });
    }
  });

  const uploadInput = document.querySelector(".upload-input");
  const uploadBox = document.querySelector(".upload");

  const readText = (file) =>
    new Promise((resolve) => {
      // 텍스트 문서만 본문을 읽어 검색에 활용(그 외는 이름만 색인).
      if (!/\.(txt|md|csv|json)$/i.test(file.name)) return resolve("");
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || "").slice(0, 4000));
      reader.onerror = () => resolve("");
      reader.readAsText(file);
    });

  uploadInput?.addEventListener("change", async () => {
    const files = [...uploadInput.files];
    if (!files.length) return;

    uploadBox.querySelector("b").textContent = `${files.length}개 문서 선택됨`;
    uploadBox.querySelector("small").textContent = files.map((file) => file.name).join(" · ");

    const done = ABC.setBusy(document.querySelector(".index-actions .primary"), "색인 중");
    try {
      const docs = await Promise.all(
        files.map(async (file) => ({ name: file.name, text: await readText(file) })),
      );
      const res = await ABC.api("/api/rag/index", { docs, use_samples: true });
      docs.forEach((d) => addToFileList(d.name, d.text ? "색인됨" : "이름만 색인(본문 없음)"));
      document.querySelector(".indexed").textContent = `✓ ${res.message}`;
      ABC.toast("업로드한 문서를 색인했습니다 — 이제 검색 근거에 포함됩니다");
    } catch {
      /* handled */
    } finally {
      done();
    }
  });
});
