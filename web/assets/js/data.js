document.addEventListener("DOMContentLoaded", async () => {
  const tbody = document.querySelector("tbody");
  const search = document.querySelector(".search-upload input");
  const uploadBtn = document.querySelector(".search-upload .primary");

  const ICONS = { 라벨: "◇", 원본: "▧", 공공데이터: "▱", 문서: "▤" };

  const rowHtml = (d) => `<tr>
    <td><input type="checkbox"></td>
    <td><b class="name-cell"><span class="name-icon">${ICONS[d.kind] || "▱"}</span>${ABC.escapeHtml(d.name)}</b></td>
    <td>${ABC.escapeHtml(d.kind)}</td>
    <td>${ABC.escapeHtml(d.count)}</td>
    <td class="mono">${ABC.escapeHtml(d.fmt)}</td>
    <td><span class="status ${d.tone}">${ABC.escapeHtml(d.state)}</span></td>
    <td>${ABC.escapeHtml(d.date)}<small>${ABC.escapeHtml(d.owner)}</small></td>
    <td class="row-actions"><button class="row-menu" type="button" aria-label="더보기">⋮</button></td></tr>`;

  // 서버에서 데이터셋 목록을 받아 테이블을 채운다. 실패 시 HTML 기본 행 유지.
  try {
    const data = await ABC.api("/api/datasets");
    if (tbody && data.datasets) tbody.innerHTML = data.datasets.map(rowHtml).join("");
  } catch {
    /* 기본 행 사용 */
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
    previewModal.querySelector(".preview-body").innerHTML = Object.entries(fields)
      .map(
        ([k, v]) =>
          `<div class="field row"><span>${ABC.escapeHtml(k)}</span><b>${ABC.escapeHtml(v)}</b></div>`,
      )
      .join("");
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
