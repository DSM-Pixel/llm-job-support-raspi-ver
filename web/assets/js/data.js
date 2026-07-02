document.addEventListener("DOMContentLoaded", async () => {
  // '이 프로젝트의 소스·검수 관리' 링크에 현재 프로젝트 딥링크 연결.
  const srcLink = document.querySelector('[data-role="src-review"]');
  const curProj = ABC.getProject ? ABC.getProject() : null;
  if (srcLink && curProj) srcLink.href = `projects.html?p=${encodeURIComponent(curProj.id)}`;

  const tbody = document.querySelector("tbody");
  const search = document.querySelector(".search-upload input");
  const uploadBtn = document.querySelector(".search-upload .primary");

  const ICONS = { 라벨: "⬡", 원본: "⊡", 공공데이터: "▱", 문서: "☰" };

  // 행에는 이름·아이콘 그대로 두고, 실제 사진은 data-img 에만 담아 '미리보기'에서 보여준다.
  const rowHtml = (d) => `<tr${d.img ? ` data-img="${d.img}"` : ""}>
    <td><input type="checkbox"></td>
    <td><b class="name-cell"><span class="name-icon">${ICONS[d.kind] || "▱"}</span>${ABC.escapeHtml(d.name)}</b></td>
    <td>${ABC.escapeHtml(d.kind)}</td>
    <td>${ABC.escapeHtml(d.count)}</td>
    <td class="mono">${ABC.escapeHtml(d.fmt)}</td>
    <td><span class="status ${d.tone}">${ABC.escapeHtml(d.state)}</span></td>
    <td>${ABC.escapeHtml(d.date)}<small>${ABC.escapeHtml(d.owner)}</small></td>
    <td class="row-actions"><button class="row-menu" type="button" aria-label="더보기">⋮</button></td></tr>`;

  // 내가 실제로 만든 작업물(라벨·분석한 이미지)을 '실제 데이터'로 표 상단에 올린다.
  // → 표는 [내 실제 작업물·업로드] + [데모 시드 카탈로그 몇 개]의 혼합이 된다.
  const myRealRows = (ABC.getArtifacts() || [])
    .filter((a) => a.image)
    .slice()
    .reverse()
    .map((a) => ({
      name: a.title || a.caption || "내 작업 이미지",
      kind: a.kind === "label" ? "라벨" : "원본",
      count: "1",
      fmt: "PNG",
      state: "내 작업",
      tone: "green",
      date: ABC.relTime ? ABC.relTime(a.ts) : "방금",
      owner: "나",
      img: a.image,
    }));

  // 서버에서 데모 시드 데이터셋 목록을 받아, 내 실제 작업물과 합쳐 표를 채운다.
  try {
    const data = await ABC.api("/api/datasets");
    if (tbody && data.datasets) {
      tbody.innerHTML = [...myRealRows, ...data.datasets].map(rowHtml).join("");
    }
  } catch {
    if (tbody && myRealRows.length) tbody.innerHTML = myRealRows.map(rowHtml).join("");
  }

  const filterRows = () => {
    const keyword = (search?.value || "").trim().toLowerCase();
    const active = document.querySelector(".chips .active")?.textContent.trim();
    tbody.querySelectorAll("tr").forEach((row) => {
      const text = row.textContent.toLowerCase();
      const type = row.children[2]?.textContent.trim();
      const matchesKeyword = !keyword || text.includes(keyword);
      const matchesType =
        active === "전체" || type === active || (active === "원본 이미지" && type === "원본");
      row.hidden = !(matchesKeyword && matchesType);
    });
  };

  document.querySelectorAll(".chips .pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      ABC.activateInGroup(pill, ".pill");
      filterRows();
    });
  });
  search?.addEventListener("input", filterRows);

  document.querySelector("thead input[type='checkbox']")?.addEventListener("change", (event) => {
    tbody.querySelectorAll("input[type='checkbox']").forEach((cb) => {
      cb.checked = event.target.checked;
    });
  });

  // 행 아무 곳이나 클릭해도 체크 토글(체크박스·⋮메뉴·이름 편집 중은 제외).
  tbody.addEventListener("click", (e) => {
    if (
      e.target.closest("input[type='checkbox']") ||
      e.target.closest(".row-menu") ||
      e.target.closest("[contenteditable='true']")
    ) {
      return;
    }
    const cb = e.target.closest("tr")?.querySelector("input[type='checkbox']");
    if (cb) cb.checked = !cb.checked;
  });

  // ── 업로드: 파일 선택 → 표에 새 행 추가(업로드 대기) ──────────────
  const guessKind = (name) => {
    const ext = name.split(".").pop().toLowerCase();
    if (["jpg", "jpeg", "png", "bmp", "mp4"].includes(ext)) return "원본";
    if (["json", "coco", "xml"].includes(ext)) return "라벨";
    if (["csv"].includes(ext)) return "공공데이터";
    if (["md", "txt", "pdf"].includes(ext)) return "문서";
    return "원본";
  };

  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.multiple = true;
  fileInput.hidden = true;
  document.body.appendChild(fileInput);

  uploadBtn?.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async () => {
    const files = [...fileInput.files];
    if (!files.length) return;
    const done = ABC.setBusy(uploadBtn, "업로드 중");
    try {
      await ABC.api("/api/datasets/upload", { name: files.map((f) => f.name).join(", ") });
      ABC.logActivity("데이터 업로드", files.map((f) => f.name).join(", "));
      files.forEach((f) => {
        tbody.insertAdjacentHTML(
          "afterbegin",
          rowHtml({
            name: f.name,
            kind: guessKind(f.name),
            count: "—",
            fmt: (f.name.split(".").pop() || "FILE").toUpperCase(),
            state: "업로드 대기",
            tone: "gray",
            date: "방금",
            owner: "나",
          }),
        );
        const tr = tbody.firstElementChild;
        // 업로드한 게 이미지 파일이면 실제 사진을 행에 저장 → '미리보기'에서 보여준다.
        if (/^image\//.test(f.type) || /\.(jpe?g|png|bmp|gif|webp)$/i.test(f.name)) {
          const reader = new FileReader();
          reader.onload = () => {
            tr.dataset.img = String(reader.result || "");
          };
          reader.readAsDataURL(f);
        }
      });
      filterRows();
      ABC.toast(`${files.length}개 파일을 데이터셋에 추가했습니다 (업로드 대기)`);
    } catch {
      /* handled */
    } finally {
      done();
      fileInput.value = "";
    }
  });

  // ── ⋮ 행 메뉴: 미리보기 / 이름 수정 / 삭제 ──────────────────────
  const menu = document.createElement("div");
  menu.className = "row-pop";
  menu.hidden = true;
  menu.innerHTML =
    '<button type="button" data-act="preview">미리보기</button>' +
    '<button type="button" data-act="edit">이름 수정</button>' +
    '<button type="button" data-act="delete">삭제</button>';
  document.body.appendChild(menu);
  let menuRow = null;

  const closeMenu = () => {
    menu.hidden = true;
    menuRow = null;
  };
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".row-pop") && !e.target.closest(".row-menu")) closeMenu();
  });

  tbody.addEventListener("click", (e) => {
    const btn = e.target.closest(".row-menu");
    if (!btn) return;
    menuRow = e.target.closest("tr");
    const r = btn.getBoundingClientRect();
    menu.style.left = `${r.right - 130 + window.scrollX}px`;
    menu.style.top = `${r.bottom + 4 + window.scrollY}px`;
    menu.hidden = false;
  });

  // 미리보기 모달(공통 modal 재사용).
  const previewModal = document.createElement("div");
  previewModal.className = "modal-overlay";
  previewModal.hidden = true;
  previewModal.innerHTML =
    '<div class="modal"><header class="modal-head"><h3>데이터셋 미리보기</h3>' +
    '<button class="modal-close" type="button" aria-label="닫기">✕</button></header>' +
    '<div class="modal-body"><div class="modal-form preview-body"></div></div></div>';
  document.body.appendChild(previewModal);
  previewModal.querySelector(".modal-close").addEventListener("click", () => {
    previewModal.hidden = true;
  });
  previewModal.addEventListener("click", (e) => {
    if (e.target === previewModal) previewModal.hidden = true;
  });

  const showPreview = (row) => {
    const c = row.children;
    const fields = {
      이름: c[1].innerText.trim(),
      유형: c[2].innerText.trim(),
      "항목 수": c[3].innerText.trim(),
      형식: c[4].innerText.trim(),
      "검수 상태": c[5].innerText.trim(),
      업데이트: c[6].innerText.trim(),
    };
    // 실제 파일(업로드·내 작업물)이 있으면 그 사진을 미리보기에 띄운다. 없으면 안내만.
    const realImg = row.dataset.img || "";
    const kind = fields["유형"];
    const fmt = fields["형식"].toUpperCase();
    const isImage = kind === "원본" || kind === "라벨" || /JPG|JPEG|PNG|BMP|MP4|프레임|COCO/.test(fmt);
    let frames = "";
    if (realImg) {
      frames =
        `<div class="preview-frames one"><img class="preview-frame" src="${realImg}" alt="${ABC.escapeHtml(fields["이름"])}" /></div>` +
        `<p class="preview-note">실제 파일 미리보기</p>`;
    } else if (isImage) {
      frames =
        `<p class="preview-note no-file">개별 파일 미리보기는 직접 업로드했거나 내가 분석·라벨한 이미지에만 표시됩니다.<br />(이 항목은 대용량·외부 연계 데이터셋이라 개별 파일이 없습니다)</p>`;
    }
    const rows = Object.entries(fields)
      .map(
        ([k, v]) =>
          `<div class="field row"><span>${ABC.escapeHtml(k)}</span><b>${ABC.escapeHtml(v)}</b></div>`,
      )
      .join("");
    previewModal.querySelector(".preview-body").innerHTML = frames + rows;
    previewModal.hidden = false;
  };

  // 삭제 확인 모달(공통 modal 재사용) — 삭제 전 한 번 더 묻는다.
  const confirmModal = document.createElement("div");
  confirmModal.className = "modal-overlay";
  confirmModal.hidden = true;
  confirmModal.innerHTML =
    '<div class="modal confirm-modal"><header class="modal-head"><h3>데이터셋 삭제</h3>' +
    '<button class="modal-close" type="button" aria-label="닫기">✕</button></header>' +
    '<div class="modal-body"><p class="confirm-text"></p></div>' +
    '<div class="modal-foot"><button class="btn modal-cancel" type="button">취소</button>' +
    '<button class="btn danger confirm-delete" type="button">삭제</button></div></div>';
  document.body.appendChild(confirmModal);

  let pendingDeleteRow = null;
  const closeConfirm = () => {
    confirmModal.hidden = true;
    pendingDeleteRow = null;
  };
  confirmModal.querySelector(".modal-close").addEventListener("click", closeConfirm);
  confirmModal.querySelector(".modal-cancel").addEventListener("click", closeConfirm);
  confirmModal.addEventListener("click", (e) => {
    if (e.target === confirmModal) closeConfirm();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !confirmModal.hidden) closeConfirm();
  });
  confirmModal.querySelector(".confirm-delete").addEventListener("click", () => {
    if (pendingDeleteRow) {
      pendingDeleteRow.remove();
      ABC.toast("데이터셋을 삭제했습니다");
    }
    closeConfirm();
  });

  const askDelete = (row) => {
    const name = row.children[1]?.innerText.trim() || "이 데이터셋";
    confirmModal.querySelector(".confirm-text").innerHTML =
      `<b>${ABC.escapeHtml(name)}</b> 을(를) 삭제할까요?<br />이 작업은 되돌릴 수 없습니다.`;
    pendingDeleteRow = row;
    confirmModal.hidden = false;
  };

  menu.addEventListener("click", (e) => {
    const act = e.target.closest("button")?.dataset.act;
    if (!act || !menuRow) return;
    const row = menuRow;
    closeMenu();
    if (act === "delete") {
      askDelete(row); // 바로 지우지 않고 확인 모달을 띄운다
    } else if (act === "edit") {
      const cell = row.querySelector(".name-cell");
      cell.setAttribute("contenteditable", "true");
      cell.focus();
      ABC.toast("이름을 수정한 뒤 Enter를 누르세요");
      const onKey = (ev) => {
        if (ev.key === "Enter") {
          ev.preventDefault();
          cell.removeAttribute("contenteditable");
          cell.removeEventListener("keydown", onKey);
          ABC.toast("이름을 수정했습니다");
        }
      };
      cell.addEventListener("keydown", onKey);
    } else if (act === "preview") {
      showPreview(row);
    }
  });
});
