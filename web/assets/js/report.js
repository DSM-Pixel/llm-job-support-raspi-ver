document.addEventListener("DOMContentLoaded", () => {
  const esc = ABC.escapeHtml;
  const reportPage = document.querySelector(".report-page");

  document.querySelectorAll(".select-list button").forEach((item) => {
    item.addEventListener("click", () => ABC.activateInGroup(item, "button"));
  });

  // 기간 입력(시작/종료). 비어 있으면 기본값(최근 30일 ~ 오늘)을 채운다.
  const startEl = document.querySelector(".date-start");
  const endEl = document.querySelector(".date-end");
  // 로컬 기준 YYYY-MM-DD (toISOString은 UTC라 KST에서 하루 어긋나므로 보정).
  const fmtDate = (d) => {
    const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  };
  if (endEl && !endEl.value) endEl.value = fmtDate(new Date());
  if (startEl && !startEl.value) {
    startEl.value = fmtDate(new Date(Date.now() - 30 * 86400000));
  }
  // 시작/종료 → "YYYY-MM-DD ~ YYYY-MM-DD" 라벨(둘 다 없으면 전체 기간).
  const periodLabel = () => {
    const s = startEl?.value || "";
    const e = endEl?.value || "";
    return s || e ? `${s} ~ ${e}` : "전체 기간";
  };

  document.querySelectorAll(".source-toggle .switch").forEach((switchEl) => {
    const row = switchEl.closest(".source-toggle");
    row?.classList.toggle("is-off", switchEl.classList.contains("off"));
    switchEl.addEventListener("click", () => {
      switchEl.classList.toggle("off");
      row?.classList.toggle("is-off", switchEl.classList.contains("off"));
    });
  });

  // 데이터 소스(통계 차트 토글 행은 제외) 중 켜진 것.
  const activeSources = () =>
    [...document.querySelectorAll(".source-toggle")]
      .filter((row) => !row.textContent.includes("통계 차트"))
      .filter((row) => !row.querySelector(".switch")?.classList.contains("off"))
      .map((row) => row.querySelector("span, b")?.textContent.trim())
      .filter(Boolean);

  // '통계 차트 포함' 토글 상태.
  const includeChart = () => {
    const row = [...document.querySelectorAll(".source-toggle")].find((r) =>
      r.textContent.includes("통계 차트"),
    );
    return !row?.querySelector(".switch")?.classList.contains("off");
  };

  // 본문(여러 문단 + '- ' 불릿)을 문단/목록 HTML로 렌더.
  const renderBody = (body) => {
    const lines = String(body || "")
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
        html += `<li>${esc(ln.replace(/^[-*•]\s+/, ""))}</li>`;
      } else {
        if (inList) {
          html += "</ul>";
          inList = false;
        }
        html += `<p>${esc(ln)}</p>`;
      }
    }
    if (inList) html += "</ul>";
    return html || "<p></p>";
  };

  // 보고서에 넣을 자료. 이미지(분석·라벨·직접첨부) 또는 RAG 도출 결과.
  // 보고서를 재생성해도 유지되도록 모듈 상태로 둔다.
  // item = {type:"image", src, caption} | {type:"rag", question, answer, source, snippet}
  let reportItems = [];

  // 첨부 자료를 보고서 문서(출처 위)에 섹션으로 주입/갱신.
  const renderItemsIntoReport = () => {
    if (!reportPage) return;
    reportPage.querySelector(".report-attachments")?.remove();
    if (!reportItems.length) return;
    const images = reportItems.filter((it) => it.type === "image");
    const rags = reportItems.filter((it) => it.type === "rag");
    let inner = "";
    if (images.length) {
      inner +=
        `<div class="report-img-grid">` +
        images
          .map(
            (it) =>
              `<figure><img src="${it.src}" alt="" /><figcaption contenteditable="true">${esc(it.caption || "")}</figcaption></figure>`,
          )
          .join("") +
        `</div>`;
    }
    inner += rags
      .map(
        (it) =>
          `<div class="report-finding"><b>RAG 도출 결과</b>` +
          `<p contenteditable="true">질문: ${esc(it.question || "")}</p>` +
          `<p contenteditable="true">결과: ${esc(it.answer || "")}</p>` +
          (it.source
            ? `<p class="rf-src">근거: ${esc(it.source)}${it.snippet ? ` — ${esc(it.snippet)}` : ""}</p>`
            : "") +
          `</div>`,
      )
      .join("");
    const section = `<section class="report-attachments"><h3 contenteditable="true">근거 자료 · 내 작업 결과</h3>${inner}</section>`;
    const footer = reportPage.querySelector("footer");
    if (footer) footer.insertAdjacentHTML("beforebegin", section);
    else reportPage.insertAdjacentHTML("beforeend", section);
  };

  // 각 섹션에 '삭제(휴지통)' 버튼을 달아 마우스 올리면 보이게 한다.
  const addSectionControls = () => {
    if (!reportPage) return;
    reportPage.querySelectorAll("section").forEach((sec) => {
      if (sec.querySelector(":scope > .sec-del")) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "sec-del";
      btn.setAttribute("contenteditable", "false");
      btn.title = "이 섹션 삭제";
      btn.setAttribute("aria-label", "이 섹션 삭제");
      btn.textContent = "🗑";
      sec.appendChild(btn);
    });
  };

  // 섹션 삭제 확인 모달 — 되돌릴 수 없으니 한 번 더 묻는다.
  const secConfirm = document.createElement("div");
  secConfirm.className = "modal-overlay";
  secConfirm.hidden = true;
  secConfirm.innerHTML =
    '<div class="modal confirm-modal"><header class="modal-head"><h3>섹션 삭제</h3>' +
    '<button class="modal-close" type="button" aria-label="닫기">✕</button></header>' +
    '<div class="modal-body"><p class="confirm-text">이 섹션을 삭제할까요?<br />이 작업은 되돌릴 수 없습니다.</p></div>' +
    '<div class="modal-foot"><button class="btn modal-cancel" type="button">취소</button>' +
    '<button class="btn danger confirm-delete" type="button">삭제</button></div></div>';
  document.body.appendChild(secConfirm);

  let pendingSec = null;
  const closeSecConfirm = () => {
    secConfirm.hidden = true;
    pendingSec = null;
  };
  secConfirm.querySelector(".modal-close").addEventListener("click", closeSecConfirm);
  secConfirm.querySelector(".modal-cancel").addEventListener("click", closeSecConfirm);
  secConfirm.addEventListener("click", (e) => {
    if (e.target === secConfirm) closeSecConfirm();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !secConfirm.hidden) closeSecConfirm();
  });
  secConfirm.querySelector(".confirm-delete").addEventListener("click", () => {
    if (pendingSec) {
      pendingSec.remove();
      ABC.toast("섹션을 삭제했습니다");
    }
    closeSecConfirm();
  });

  // 휴지통 클릭 → 바로 지우지 않고 확인 모달(섹션 이름 표시).
  reportPage?.addEventListener("click", (e) => {
    const del = e.target.closest(".sec-del");
    if (!del) return;
    pendingSec = del.closest("section");
    const name = pendingSec?.querySelector("h3")?.textContent.trim() || "이 섹션";
    secConfirm.querySelector(".confirm-text").innerHTML =
      `‘${esc(name)}’ 섹션을 삭제하시겠습니까?<br />이 작업은 되돌릴 수 없습니다.`;
    secConfirm.hidden = false;
  });

  // 마지막으로 렌더한 보고서(AI 수정 시 제목·섹션만 교체하고 나머지는 유지).
  let lastReport = null;

  // 구조화 응답 → 편집 가능한 제출 보고서 문서로 렌더.
  const renderReport = (r) => {
    lastReport = r;
    const sections = (r.sections || [])
      .map(
        (s) =>
          `<section><h3 contenteditable="true">${esc(s.heading)}</h3><div class="sec-body" contenteditable="true">${renderBody(s.body)}</div></section>`,
      )
      .join("");

    let table = "";
    if (r.table) {
      const head = r.table.columns.map((c) => `<th>${esc(c)}</th>`).join("");
      const body = r.table.rows
        .map((row) => `<tr>${row.map((c) => `<td contenteditable="true">${esc(c)}</td>`).join("")}</tr>`)
        .join("");
      table = `<section><h3 contenteditable="true">${esc(r.table.caption)}</h3><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
    }

    const sources = (r.sources || [])
      .map((s) =>
        s && typeof s === "object"
          ? `<a class="pill src-link" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`
          : `<span class="pill">${esc(s)}</span>`,
      )
      .join("");

    reportPage.innerHTML = `
      <header>
        <p>${esc(r.org)} · ${esc(r.report_type)}</p>
        <h2 contenteditable="true">${esc(r.title)}</h2>
        <span>${esc(r.subtitle)}</span>
      </header>
      ${sections}
      ${table}
      <footer><b>출처</b>${sources}</footer>`;
    renderItemsIntoReport(); // 재생성 시에도 첨부 자료 유지
    addSectionControls(); // 섹션 삭제 버튼 부착
  };

  // 생성 실패로 '로딩 중'이 멈춰 있으면 안내 문구로 대체(가짜 보고서 대신).
  const clearLoadingIfStuck = () => {
    if (reportPage?.querySelector(".report-loading")) {
      reportPage.innerHTML =
        `<div class="report-empty"><p>보고서를 불러오지 못했습니다.</p>` +
        `<p>왼쪽에서 기간·유형을 정하고 ‘보고서 생성’을 눌러주세요.</p></div>`;
    }
  };

  // 추가 예정(staged) 자료 안내 — 본문에는 '보고서 생성' 시에만 반영된다.
  const stagedNote = document.querySelector(".staged-note");
  const updateStagedNote = () => {
    if (!stagedNote) return;
    const n = reportItems.length;
    stagedNote.hidden = n === 0;
    stagedNote.textContent = n
      ? `추가 예정 자료 ${n}건 — ‘보고서 생성’을 누르면 본문에 반영됩니다`
      : "";
  };

  // ── 내 작업에서 가져오기(아티팩트 picker) ───────────────────────
  const artifactListEl = document.querySelector(".artifact-list");

  const renderArtifactPicker = () => {
    if (!artifactListEl) return;
    const arts = ABC.getArtifacts().slice().reverse(); // 최신 먼저
    if (!arts.length) {
      artifactListEl.innerHTML =
        `<p class="artifact-empty">아직 분석·검색한 자료가 없습니다. 이미지 분석·라벨링이나 RAG 검색을 사용하면 여기에 나타납니다.</p>`;
      return;
    }
    artifactListEl.innerHTML = arts
      .map((a) => {
        const thumb = a.image
          ? `<img src="${a.image}" alt="" />`
          : `<span class="artifact-ic">${a.kind === "rag" ? "⌕" : "▣"}</span>`;
        const sub = a.kind === "rag" ? a.question || a.title : a.caption || a.title;
        return `<div class="artifact-item" data-ts="${a.ts}"><div class="artifact-thumb">${thumb}</div><div class="artifact-meta"><b>${esc(a.title)}</b><small>${esc(sub || "")}</small></div><button type="button" class="btn artifact-add">추가</button></div>`;
      })
      .join("");
  };

  // 아티팩트를 보고서 자료로 staged.
  const addArtifact = (a) => {
    if (a.kind === "rag") {
      reportItems.push({
        type: "rag",
        question: a.question,
        answer: a.answer,
        source: a.source,
        snippet: a.snippet,
      });
    } else if (a.image) {
      reportItems.push({ type: "image", src: a.image, caption: a.caption || a.title });
    }
    renderThumbs();
    updateStagedNote();
    ABC.toast("자료를 추가했습니다 — ‘보고서 생성’ 시 반영됩니다");
  };

  // 아티팩트 상세 모달 — 사진 크게 보기 + 일시·결과·근거 등.
  const artModal = document.createElement("div");
  artModal.className = "modal-overlay";
  artModal.hidden = true;
  artModal.innerHTML =
    '<div class="modal art-modal"><header class="modal-head"><h3 class="art-title"></h3>' +
    '<button class="modal-close" type="button" aria-label="닫기">✕</button></header>' +
    '<div class="modal-body"><div class="art-detail"></div></div>' +
    '<div class="modal-foot"><button class="btn modal-cancel" type="button">닫기</button>' +
    '<button class="btn primary art-add" type="button">보고서에 추가</button></div></div>';
  document.body.appendChild(artModal);

  let artModalTs = null;
  const closeArt = () => {
    artModal.hidden = true;
    artModalTs = null;
  };
  artModal.querySelector(".modal-close").addEventListener("click", closeArt);
  artModal.querySelector(".modal-cancel").addEventListener("click", closeArt);
  artModal.addEventListener("click", (e) => {
    if (e.target === artModal) closeArt();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !artModal.hidden) closeArt();
  });
  artModal.querySelector(".art-add").addEventListener("click", () => {
    const a = ABC.getArtifacts().find((x) => x.ts === artModalTs);
    if (a) addArtifact(a);
    closeArt();
  });

  const fmtTs = (ts) => {
    try {
      return new Date(ts).toLocaleString("ko-KR");
    } catch {
      return "";
    }
  };

  const openArtDetail = (a) => {
    artModalTs = a.ts;
    artModal.querySelector(".art-title").textContent = a.title || "자료";
    const rows = [`<div class="art-row"><span>일시</span><b>${esc(fmtTs(a.ts))}</b></div>`];
    if (a.page) rows.push(`<div class="art-row"><span>출처 화면</span><b>${esc(a.page)}</b></div>`);
    let body = "";
    if (a.image) {
      body += `<div class="art-image"><img src="${a.image}" alt="${esc(a.title || "")}" /></div>`;
      if (a.caption) rows.push(`<div class="art-row"><span>결과</span><b>${esc(a.caption)}</b></div>`);
    }
    if (a.kind === "rag") {
      if (a.question) rows.push(`<div class="art-row"><span>질문</span><b>${esc(a.question)}</b></div>`);
      if (a.answer) rows.push(`<div class="art-row"><span>도출</span><b>${esc(a.answer)}</b></div>`);
      if (a.source) {
        rows.push(
          `<div class="art-row"><span>근거</span><b>${esc(a.source)}${a.snippet ? ` — ${esc(a.snippet)}` : ""}</b></div>`,
        );
      }
    }
    artModal.querySelector(".art-detail").innerHTML = `${body}<div class="art-rows">${rows.join("")}</div>`;
    artModal.hidden = false;
  };

  artifactListEl?.addEventListener("click", (e) => {
    const item = e.target.closest(".artifact-item");
    if (!item) return;
    const a = ABC.getArtifacts().find((x) => x.ts === Number(item.dataset.ts));
    if (!a) return;
    if (e.target.closest(".artifact-add")) {
      addArtifact(a); // '추가' 버튼 → 바로 staged
    } else {
      openArtDetail(a); // 썸네일·내용 클릭 → 상세 모달(사진 크게·날짜 등)
    }
  });

  renderArtifactPicker();

  // ── 직접 사진 첨부(왼쪽 패널) ───────────────────────────────────
  const imgInput = document.querySelector(".report-image-input");
  const thumbsEl = document.querySelector(".report-thumbs");

  // 이미지 타입 자료만 썸네일로 보여주고 ✕로 개별 삭제.
  const renderThumbs = () => {
    if (!thumbsEl) return;
    thumbsEl.innerHTML = reportItems
      .map((it, i) =>
        it.type === "image"
          ? `<div class="report-thumb"><img src="${it.src}" alt="첨부 ${i + 1}" /><button type="button" class="thumb-del" data-i="${i}" aria-label="삭제">✕</button></div>`
          : "",
      )
      .join("");
  };

  document
    .querySelector(".add-report-image")
    ?.addEventListener("click", () => imgInput?.click());

  imgInput?.addEventListener("change", () => {
    const files = [...(imgInput.files || [])].filter((f) => f.type.startsWith("image/"));
    if (!files.length) return;
    let remaining = files.length;
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        reportItems.push({ type: "image", src: String(reader.result || ""), caption: "첨부 사진" });
        if (--remaining === 0) {
          renderThumbs();
          updateStagedNote();
          ABC.toast(`사진 ${files.length}장 추가 — ‘보고서 생성’ 시 반영됩니다`);
        }
      };
      reader.readAsDataURL(file);
    });
    imgInput.value = ""; // 같은 파일 다시 선택 가능
  });

  thumbsEl?.addEventListener("click", (e) => {
    const del = e.target.closest(".thumb-del");
    if (!del) return;
    reportItems.splice(Number(del.dataset.i), 1);
    renderThumbs();
    updateStagedNote();
  });

  // web=true 면 인터넷 웹 검색(Gemini 그라운딩) 기반, false 면 빠른 예시.
  // query 가 있으면(예: RAG에서 넘어온 질문) 그 주제로 생성.
  const generate = async (button, web, query) => {
    const reportType =
      document.querySelector(".select-list .active")?.textContent.trim() || "현황 분석";
    const period = periodLabel();
    const done = button ? ABC.setBusy(button, web ? "웹 검색 중…" : "생성 중") : () => {};
    try {
      const result = await ABC.api(web ? "/api/report/web" : "/api/report", {
        report_type: reportType,
        period,
        sources: activeSources(),
        include_chart: includeChart(),
        query: query || "",
      });
      renderReport(result);
      if (button) {
        ABC.toast(
          result.backend === "GEMINI_WEB"
            ? "웹 검색으로 보고서를 생성했습니다 (출처 클릭 가능, 본문 수정 가능)"
            : "보고서를 생성했습니다 (본문 수정 가능)",
        );
      }
    } catch {
      /* api()가 toast */
    } finally {
      clearLoadingIfStuck();
      done();
    }
  };

  // 내 웹 활동(질의·검색·이미지 분석·라벨·업로드)을 날짜 범위로 필터해 분석·통계 보고서 생성.
  const generateActivity = async (button) => {
    const reportType =
      document.querySelector(".select-list .active")?.textContent.trim() || "활동 요약";
    const start = startEl?.value || "";
    const end = endEl?.value || "";
    // localStorage 활동을 날짜 범위(ts 기준)로 필터.
    const startMs = start ? new Date(`${start}T00:00:00`).getTime() : -Infinity;
    const endMs = end ? new Date(`${end}T23:59:59`).getTime() : Infinity;
    const activities = ABC.getActivity().filter((a) => a.ts >= startMs && a.ts <= endMs);
    const done = button ? ABC.setBusy(button, "분석 중…") : () => {};
    try {
      const result = await ABC.api("/api/report/activity", {
        activities,
        start,
        end,
        report_type: reportType,
        include_chart: includeChart(),
      });
      renderReport(result);
      if (button) {
        ABC.toast(
          activities.length
            ? `내 활동 ${activities.length}건을 분석해 보고서를 생성했습니다 (본문 수정 가능)`
            : "선택한 기간에 기록된 활동이 없습니다 — 질의·검색·이미지 분석을 사용하면 집계됩니다",
        );
      }
    } catch {
      /* api()가 toast */
    } finally {
      clearLoadingIfStuck();
      done();
    }
  };

  // "보고서 생성" 버튼 = 내 활동 기반 통계 보고서 생성(기본 동작).
  document
    .querySelector(".report-form .primary")
    ?.addEventListener("click", (e) => generateActivity(e.currentTarget));

  // RAG 검색 결과를 그대로 이어받아 보고서로 생성.
  const generateFromRag = async (ctx) => {
    const reportType =
      document.querySelector(".select-list .active")?.textContent.trim() || "현황 분석";
    const period = periodLabel();
    const btn = document.querySelector(".report-form .primary");
    const done = ABC.setBusy(btn, "생성 중…");
    try {
      const result = await ABC.api("/api/report/from-rag", {
        question: ctx.question,
        answer: ctx.answer,
        sources: ctx.sources,
        report_type: reportType,
        period,
        include_chart: includeChart(),
      });
      renderReport(result);
      ABC.toast("RAG 검색 내용으로 보고서를 생성했습니다 (본문 수정 가능)");
    } catch {
      /* api()가 toast */
    } finally {
      clearLoadingIfStuck();
      done();
    }
  };

  const params = new URLSearchParams(location.search);
  let ragCtx = null;
  if (params.get("from") === "rag") {
    try {
      ragCtx = JSON.parse(sessionStorage.getItem("ragReport") || "null");
    } catch {
      ragCtx = null;
    }
  }
  const incomingQuery = params.get("q");

  if (ragCtx) {
    generateFromRag(ragCtx);
  } else if (incomingQuery) {
    ABC.toast(`‘${incomingQuery}’ 관련 보고서를 생성합니다…`);
    generate(document.querySelector(".report-form .primary"), true, incomingQuery);
  } else {
    // 기본 진입: 내 웹 활동을 분석한 활동 요약 보고서.
    generateActivity(null);
  }

  // 내보내기/공유는 (수정 반영된) 문서 전체 텍스트를 사용. 삭제 버튼(🗑)은 제외.
  // 보고서를 가독성 있는 일반 텍스트로 — 제목·구분선·섹션 제목·불릿·표·출처에
  // 적절한 줄바꿈/들여쓰기를 넣어 복사·공유 시 읽기 좋게 만든다.
  const getReportText = () => {
    if (!reportPage) return "보고서";
    const root = reportPage.cloneNode(true);
    root.querySelectorAll(".sec-del").forEach((b) => b.remove());
    const out = [];
    const push = (s = "") => out.push(s);
    const txt = (el) => (el ? el.innerText.replace(/[ \t]+\n/g, "\n").trim() : "");

    const header = root.querySelector("header");
    if (header) {
      const title = txt(header.querySelector("h2"));
      const sub = txt(header.querySelector("span"));
      const org = txt(header.querySelector("p"));
      if (title) push(title);
      if (sub) push(sub);
      if (org) push(`(${org})`);
      push();
      push("─".repeat(34));
      push();
    }

    root.querySelectorAll(":scope > section").forEach((sec) => {
      const heading = txt(sec.querySelector(":scope > h3"));
      if (heading) {
        push(`■ ${heading}`);
        push();
      }
      const table = sec.querySelector("table");
      if (table) {
        table.querySelectorAll("tr").forEach((tr) => {
          push([...tr.children].map((c) => c.innerText.trim()).join("  |  "));
        });
        push();
        return;
      }
      // RAG 도출 결과 블록
      sec.querySelectorAll(".report-finding").forEach((f) => {
        f.querySelectorAll("b, p").forEach((el) => {
          const t = txt(el);
          if (t) push(el.tagName === "B" ? `· ${t}` : `  ${t}`);
        });
        push();
      });
      // 첨부 이미지 캡션
      sec.querySelectorAll("figcaption").forEach((c) => {
        const t = txt(c);
        if (t) push(`[이미지] ${t}`);
      });
      // 본문(문단/불릿)
      const body = sec.querySelector(".sec-body");
      if (body) {
        body.querySelectorAll("p, li").forEach((el) => {
          const t = txt(el);
          if (t) push(el.tagName === "LI" ? `  • ${t}` : t);
        });
        push();
      }
    });

    const footer = root.querySelector("footer");
    if (footer) {
      const sources = [...footer.querySelectorAll(".pill, .src-link")]
        .map((p) => p.innerText.trim())
        .filter(Boolean);
      if (sources.length) push(`출처: ${sources.join(", ")}`);
    }

    return out.join("\n").replace(/\n{3,}/g, "\n\n").trim() || "보고서";
  };

  document.querySelector(".copy-report")?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(getReportText());
      ABC.toast("보고서 내용이 복사되었습니다");
    } catch {
      ABC.toast("복사를 지원하지 않는 브라우저입니다");
    }
  });

  document.querySelector(".pdf-report")?.addEventListener("click", () => window.print());

  document.querySelector(".share-report")?.addEventListener("click", async () => {
    const title = reportPage?.querySelector("h2")?.textContent.trim() || "보고서";
    const text = getReportText();
    try {
      if (navigator.share) {
        await navigator.share({ title, text });
        ABC.toast("공유를 완료했습니다");
        return;
      }
      await navigator.clipboard.writeText(text);
      ABC.toast("공유 기능이 없어 보고서 내용을 복사했습니다");
    } catch {
      ABC.toast("공유를 취소했거나 지원하지 않습니다");
    }
  });

  // AI 대화 패널 = 보고서 편집기. 수정 지시면 본문을 다시 쓰고, 질문이면 답한다.
  // 예: "서론·본론·결론으로 나눠줘", "서론에 포트홀이 뭔지 추가해줘".
  ABC.registerAskHandler(async (q) => {
    const r = await ABC.api("/api/report/revise", {
      content: reportPage.innerText,
      instruction: q,
    });
    if (r.mode === "edit" && r.sections && r.sections.length) {
      // 제목·섹션만 교체하고 머리말·통계표·출처·첨부 자료는 유지.
      renderReport({
        ...(lastReport || {}),
        title: r.title || lastReport?.title || "보고서",
        sections: r.sections,
      });
      return "보고서를 수정했습니다. 왼쪽 미리보기를 확인하세요. (본문을 직접 더 고칠 수도 있어요)";
    }
    return r.answer;
  }, "보고서를 수정하거나 질문하세요 — 예: ‘서론·본론·결론으로 나눠줘’");
});
