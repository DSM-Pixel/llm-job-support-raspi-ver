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

  // 추천 질문 클릭(델리게이션) — 목록이 파일에 따라 갱신돼도 동작.
  document.querySelector(".chips")?.addEventListener("click", (e) => {
    const pill = e.target.closest(".pill");
    if (!pill) return;
    ABC.activateInGroup(pill, ".pill");
    askInput.value = pill.textContent.trim();
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
      await loadFiles();
      ABC.toast("문서 색인이 완료되었습니다 — 참고중인 파일 갱신됨");
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
      await loadFiles();
      ABC.toast("색인을 초기화했습니다 — 샘플 문서만 남김");
    } catch {
      /* handled */
    } finally {
      done();
    }
  });

  const fileList = document.querySelector(".file-list");

  const fileDelBtn = '<button class="file-del" type="button" title="색인에서 삭제" aria-label="삭제">✕</button>';

  // 참고중인 파일 목록을 백엔드에서 받아 렌더(실제 청크 수 표시).
  const loadFiles = async () => {
    if (!fileList) return;
    try {
      const r = await ABC.api("/api/rag/files");
      fileList.innerHTML = (r.files || [])
        .map(
          (f) =>
            `<li><i>▤</i><b>${ABC.escapeHtml(f.source)}</b><small>청크 ${f.chunks}개</small>${fileDelBtn}</li>`,
        )
        .join("");
      // 추천 질문을 참고 파일에 맞춰 갱신.
      const chips = document.querySelector(".chips");
      if (chips && r.suggestions && r.suggestions.length) {
        chips.innerHTML =
          "<span>추천</span>" +
          r.suggestions
            .map((q, i) => `<span class="pill${i === 0 ? " active" : ""}">${ABC.escapeHtml(q)}</span>`)
            .join("");
      }
    } catch {
      /* 정적 항목 유지 */
    }
  };

  const removeFile = async (name) => {
    try {
      const r = await ABC.api("/api/rag/remove", { source: name });
      await loadFiles();
      ABC.toast(r.message || `‘${name}’ 삭제됨`);
    } catch {
      /* api()가 toast */
    }
  };

  loadFiles(); // 진입 시 실제 색인 파일 목록 표시

  // 참고중인 파일 클릭 → 문서 내용 열람(모달).
  const docModal = document.createElement("div");
  docModal.className = "modal-overlay";
  docModal.hidden = true;
  docModal.innerHTML =
    '<div class="modal"><header class="modal-head"><h3 class="doc-title"></h3>' +
    '<button class="modal-close" type="button" aria-label="닫기">✕</button></header>' +
    '<div class="modal-body"><div class="doc-body"></div></div></div>';
  document.body.appendChild(docModal);
  const closeDoc = () => {
    docModal.hidden = true;
  };
  docModal.querySelector(".modal-close").addEventListener("click", closeDoc);
  docModal.addEventListener("click", (e) => {
    if (e.target === docModal) closeDoc();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !docModal.hidden) closeDoc();
  });

  const openDoc = async (name) => {
    try {
      const r = await ABC.api(`/api/rag/doc?source=${encodeURIComponent(name)}`);
      docModal.querySelector(".doc-title").textContent = name;
      docModal.querySelector(".doc-body").innerHTML = r.found
        ? r.chunks
            .map(
              (c, i) =>
                `<p class="doc-chunk"><span class="doc-no">청크 ${i + 1}</span>${ABC.escapeHtml(c)}</p>`,
            )
            .join("")
        : "<p class='doc-empty'>이 문서는 본문이 색인되지 않았습니다(이름만 등록).</p>";
      docModal.hidden = false;
    } catch {
      /* api()가 toast 표시 */
    }
  };

  fileList?.addEventListener("click", (e) => {
    const li = e.target.closest("li");
    const name = li?.querySelector("b")?.textContent.trim();
    if (!name) return;
    if (e.target.closest(".file-del")) {
      removeFile(name); // 삭제 버튼 → 색인에서 제거
      return;
    }
    openDoc(name); // 그 외 클릭 → 문서 열람
  });

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
        await loadFiles();
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
        // 지금 RAG에서 하던 내용(질문·AI답변·근거 문서)을 그대로 보고서로 이어받기.
        const sources = [...document.querySelectorAll(".source-list .source")].map((card) => ({
          source: card.querySelector("b")?.textContent.replace(/^\d+\s*/, "").trim() || "",
          text: card.querySelector("p")?.textContent.trim() || "",
        }));
        const ctx = {
          question: askInput.value.trim() || "도로 파손 현황",
          answer: answer.textContent.trim(),
          sources,
        };
        sessionStorage.setItem("ragReport", JSON.stringify(ctx));
        window.location.href = "report.html?from=rag";
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
      await loadFiles();
      document.querySelector(".indexed").textContent = `✓ ${res.message}`;
      ABC.toast("업로드한 문서를 색인했습니다 — 이제 검색 근거에 포함됩니다");
    } catch {
      /* handled */
    } finally {
      done();
    }
  });
});
