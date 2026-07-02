document.addEventListener("DOMContentLoaded", () => {
  // 현재 프로젝트 id — RAG 지식이 프로젝트별로 분리되도록 모든 호출에 실어 보낸다.
  const PID = () => (ABC.getProject() || {}).id || "";
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
      const result = await ABC.api("/api/rag/search", { query, project: PID() });
      answer.innerHTML = result.answer;
      confidence.textContent = result.found ? `연관도 ${result.confidence}%` : "근거 없음";
      if (methodTag) methodTag.textContent = result.method;
      if (meta) meta.textContent = `top-K ${result.top_k} · ${result.chunks} chunks · ${result.elapsed}`;
      renderSources(result.sources);
      ABC.logActivity("RAG 검색", query);
      // 근거를 찾았으면 보고서에 넣을 산출물로 저장(질문·근거파일·도출 결과).
      if (result.found) {
        const top = result.sources?.[0] || {};
        ABC.saveArtifact({
          kind: "rag",
          title: "RAG 검색 결과",
          question: query,
          answer: String(result.answer || "")
            .replace(/<[^>]+>/g, "")
            .slice(0, 300),
          source: top.source || "",
          snippet: String(top.text || "").slice(0, 160),
        });
      }
      ABC.toast(result.found ? "검색 결과가 갱신되었습니다" : "참고 문서에 관련 정보가 없습니다");
    } catch {
      /* api()가 이미 toast 표시 */
    } finally {
      done();
    }
  };

  askButton?.addEventListener("click", search);
  askInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") search();
  });

  // 자연어 질의에서 ?q=로 연계돼 넘어오면 그 질문을 색인 데이터에서 바로 검색.
  const incomingQ = new URLSearchParams(location.search).get("q");
  if (incomingQ && askInput) {
    askInput.value = incomingQ;
    search();
  }

  // '샘플 점검 문서 사용' 토글 → 즉시 샘플 포함/제외(참고 파일 목록 갱신).
  document.querySelector(".toggle-row .switch")?.addEventListener("click", async (event) => {
    const sw = event.currentTarget;
    sw.classList.toggle("off");
    const on = !sw.classList.contains("off");
    try {
      await ABC.api("/api/rag/samples", { on, project: PID() });
      await loadFiles();
      ABC.toast(on ? "샘플 문서를 포함했습니다" : "샘플 문서를 제외했습니다");
    } catch {
      /* handled */
    }
  });
  // 색인/초기화/선택 처리는 아래(업로드 스테이징 영역)에서 일괄 정의한다.

  const fileList = document.querySelector(".file-list");

  const fileDelBtn = '<button class="file-del" type="button" title="색인에서 삭제" aria-label="삭제">✕</button>';

  // 참고중인 파일 목록을 백엔드에서 받아 렌더(실제 청크 수 표시).
  const loadFiles = async () => {
    if (!fileList) return;
    try {
      const r = await ABC.api(`/api/rag/files?project=${encodeURIComponent(PID())}`);
      fileList.innerHTML = (r.files || [])
        .map(
          (f) =>
            `<li><i>☰</i><b>${ABC.escapeHtml(f.source)}</b><small>청크 ${f.chunks}개</small>${fileDelBtn}</li>`,
        )
        .join("");
    } catch {
      /* 정적 항목 유지 */
    }
  };

  const removeFile = async (name) => {
    try {
      const r = await ABC.api("/api/rag/remove", { source: name, project: PID() });
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
      const r = await ABC.api(`/api/rag/doc?source=${encodeURIComponent(name)}&project=${encodeURIComponent(PID())}`);
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
        const res = await ABC.api("/api/rag/index", { docs, use_samples: true, project: PID() });
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

  const uploadInput = document.querySelector(".upload-input");
  const uploadBox = document.querySelector(".upload");
  const stagedEl = document.querySelector(".staged-files");
  const indexBtn = document.querySelector(".index-btn");
  const stageClearBtn = document.querySelector(".stage-clear");
  const resetAllBtn = document.querySelector(".reset-all");

  const readText = (file) =>
    new Promise((resolve) => {
      // 텍스트 문서만 본문을 읽어 검색에 활용(그 외는 이름만 색인).
      if (!/\.(txt|md|csv|json)$/i.test(file.name)) return resolve("");
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || "").slice(0, 4000));
      reader.onerror = () => resolve("");
      reader.readAsText(file);
    });

  // 색인 전 '선택만' 보관(스테이징).
  let stagedDocs = [];

  const renderStaged = () => {
    if (!stagedEl) return;
    stagedEl.hidden = stagedDocs.length === 0;
    stagedEl.innerHTML = stagedDocs.length
      ? `<b>선택됨 ${stagedDocs.length}개</b> — ${stagedDocs.map((d) => ABC.escapeHtml(d.name)).join(", ")}`
      : "";
    if (uploadBox) {
      uploadBox.querySelector("b").textContent = stagedDocs.length
        ? `${stagedDocs.length}개 문서 선택됨`
        : "내 문서 선택";
    }
  };

  // 파일 선택 → 스테이징만(아직 참고중인 파일에 추가하지 않음).
  uploadInput?.addEventListener("change", async () => {
    const files = [...uploadInput.files];
    if (!files.length) return;
    const docs = await Promise.all(
      files.map(async (file) => ({ name: file.name, text: await readText(file) })),
    );
    docs.forEach((d) => {
      if (!stagedDocs.some((s) => s.name === d.name)) stagedDocs.push(d);
    });
    renderStaged();
    ABC.toast(`${files.length}개 선택됨 — ‘문서 색인’을 누르면 추가됩니다`);
  });

  // 문서 색인 → 스테이징한 문서를 참고중인 파일에 추가.
  indexBtn?.addEventListener("click", async () => {
    if (!stagedDocs.length) {
      ABC.toast("먼저 문서를 선택하세요");
      return;
    }
    const done = ABC.setBusy(indexBtn, "색인 중");
    const stagedNames = stagedDocs.map((d) => d.name).join(", ");
    try {
      const useSamples = !document.querySelector(".toggle-row .switch")?.classList.contains("off");
      const res = await ABC.api("/api/rag/index", { docs: stagedDocs, use_samples: useSamples, project: PID() });
      stagedDocs = [];
      renderStaged();
      if (uploadInput) uploadInput.value = "";
      await loadFiles();
      document.querySelector(".indexed").textContent = `✓ ${res.message}`;
      ABC.logActivity("문서 색인", stagedNames);
      ABC.toast("선택한 문서를 참고중인 파일에 추가했습니다");
    } catch {
      /* handled */
    } finally {
      done();
    }
  });

  // 선택 취소 → 스테이징만 비움(참고중인 파일은 그대로).
  stageClearBtn?.addEventListener("click", () => {
    if (!stagedDocs.length) {
      ABC.toast("취소할 선택이 없습니다");
      return;
    }
    stagedDocs = [];
    if (uploadInput) uploadInput.value = "";
    renderStaged();
    ABC.toast("선택을 취소했습니다");
  });

  // 전체 참고 파일 초기화 → 추가/삭제 내역을 비우고 샘플만 남김.
  resetAllBtn?.addEventListener("click", async () => {
    const done = ABC.setBusy(resetAllBtn, "초기화 중");
    try {
      const result = await ABC.api("/api/rag/reset", { project: PID() });
      document.querySelector(".toggle-row .switch")?.classList.add("off"); // 샘플 토글 OFF 동기화
      await loadFiles();
      document.querySelector(".indexed").textContent = `✓ ${result.message}`;
      ABC.toast("참고 파일을 전체 초기화했습니다 (샘플 포함) — 샘플 토글을 켜면 복원");
    } catch {
      /* handled */
    } finally {
      done();
    }
  });
});
