document.addEventListener("DOMContentLoaded", () => {
  const analyzeButton = document.querySelector(".label-panel .analyze-btn");
  const resultList = document.querySelector(".finding-list");
  const confidence = document.querySelector(".result-card .status");
  const customInput = document.querySelector(".label-panel textarea");

  const fileInput = document.querySelector(".image-input");
  const previewImg = document.querySelector(".preview-img");
  const preview = document.querySelector(".road-preview");
  const previewBoxesEl = document.querySelector(".preview-boxes");
  const sampleName = document.querySelector(".sample-name");

  // ── 다중 이미지 모델 ─────────────────────────────────────────────
  // 여러 사진(파일 다중 선택 / 폴더)을 올려 각각 분석·라벨한다.
  // 이미지 = {name, url, file, sample, savedBoxes:[], result:{html,confText,confClass}|null}
  const SAMPLE_NAME = sampleName?.textContent.trim() || "road_2026Q1_0142.jpg";
  let images = [
    { name: SAMPLE_NAME, url: "", file: null, sample: true, savedBoxes: [], result: null },
  ];
  let activeIdx = 0;

  // 활성 이미지에서 동기화되는 현재 작업 대상(모달·분석·내보내기가 참조).
  let imageName = SAMPLE_NAME;
  let imageURL = "";
  let imageFile = null;
  let savedBoxes = images[0].savedBoxes;

  const stripEl = document.querySelector(".image-strip");
  const countEl = document.querySelector(".image-count");
  const folderInput = document.querySelector(".folder-input");
  const batchBtn = document.querySelector(".batch-label");

  // ════════════════════════════════════════════════════════════════
  //  라벨링 모달 — 큰 이미지 위에서 박스 그리기/편집/삭제
  // ════════════════════════════════════════════════════════════════
  const modal = document.querySelector("#label-modal");
  const stage = modal.querySelector(".canvas-stage");
  const canvasImg = modal.querySelector(".canvas-img");
  const boxesEl = modal.querySelector(".canvas-boxes");
  const listEl = modal.querySelector(".box-list");
  const classInput = modal.querySelector(".modal-class");
  const totalEl = modal.querySelector(".box-total");
  const nameEl = modal.querySelector(".modal-imgname");
  const navEl = modal.querySelector(".modal-nav");
  const posEl = modal.querySelector(".modal-pos");
  const prevBtn = modal.querySelector(".modal-prev");
  const nextBtn = modal.querySelector(".modal-next");

  let boxes = []; // {x,y,w,h (%, 0~100), label, confidence|null}
  let selected = -1;

  const clone = (arr) => arr.map((b) => ({ ...b }));

  const setImage = () => {
    if (imageURL) {
      canvasImg.src = imageURL;
      stage.classList.add("has-image");
    } else {
      canvasImg.removeAttribute("src");
      stage.classList.remove("has-image");
    }
    nameEl.textContent = imageName;
  };

  const render = () => {
    boxesEl.innerHTML = boxes
      .map((b, i) => {
        return `<div class="draw-box${i === selected ? " selected" : ""}" data-i="${i}" style="left:${b.x}%;top:${b.y}%;width:${b.w}%;height:${b.h}%"><span class="tag">${ABC.escapeHtml(b.label)}${b.confidence != null ? ` ${b.confidence}%` : ""}</span></div>`;
      })
      .join("");
    listEl.innerHTML = boxes
      .map((b, i) => {
        return `<li class="${i === selected ? "selected" : ""}" data-i="${i}"><input value="${ABC.escapeHtml(b.label)}" /><span class="conf">${b.confidence != null ? `${b.confidence}%` : "—"}</span><button class="del" type="button" aria-label="삭제">✕</button></li>`;
      })
      .join("");
    totalEl.textContent = String(boxes.length);
  };

  // 같은(거의 동일한) 박스인지 — 라벨 동일 + 좌표 2% 이내.
  const sameBox = (a, b) =>
    a.label === b.label &&
    Math.abs(a.x - b.x) < 2 &&
    Math.abs(a.y - b.y) < 2 &&
    Math.abs(a.w - b.w) < 2 &&
    Math.abs(a.h - b.h) < 2;

  // 중복이면 추가하지 않음. 추가됐으면 true.
  const addBox = (box) => {
    if (boxes.some((e) => sameBox(e, box))) return false;
    boxes.push(box);
    return true;
  };

  // 미리보기(작은 썸네일) 위 박스 오버레이 — 저장된 박스를 보여준다.
  const renderPreviewBoxes = () => {
    if (!previewBoxesEl) return;
    previewBoxesEl.innerHTML = savedBoxes
      .map(
        (b) =>
          `<div class="pbox ${b.tone || ""}" style="left:${b.x}%;top:${b.y}%;width:${b.w}%;height:${b.h}%"><span>${ABC.escapeHtml(b.label)}</span></div>`,
      )
      .join("");
  };

  const persist = () => {
    images[activeIdx].savedBoxes = clone(boxes);
    savedBoxes = images[activeIdx].savedBoxes;
    renderPreviewBoxes();
    renderStrip();
  };

  // 분석 결과 패널을 이미지별로 복원(전환 시).
  const restoreResult = (im) => {
    if (im.result) {
      resultList.innerHTML = im.result.html;
      confidence.textContent = im.result.confText;
      confidence.className = im.result.confClass;
    } else {
      resultList.innerHTML =
        '<li class="finding-empty">아직 분석 전입니다. 왼쪽 ‘분석하기’를 누르세요.</li>';
      confidence.textContent = "분석 전";
      confidence.className = "status gray";
    }
  };

  // 현재 분석 결과를 활성 이미지에 저장.
  const saveCurResult = () => {
    images[activeIdx].result = {
      html: resultList.innerHTML,
      confText: confidence.textContent,
      confClass: confidence.className,
    };
  };

  // 이미지 갤러리(스트립) 렌더 — 클릭으로 전환, ✕로 제거, 배지로 라벨 수.
  const renderStrip = () => {
    if (!stripEl) return;
    stripEl.innerHTML = images
      .map((im, i) => {
        const thumb = im.url
          ? `<img src="${im.url}" alt="" />`
          : '<span class="strip-ph">샘플</span>';
        const n = im.savedBoxes.length;
        const badge = n ? `<i class="strip-count" title="라벨 ${n}개">${n}</i>` : "";
        const del = im.sample
          ? ""
          : `<span class="strip-del" data-del="${i}" role="button" aria-label="제거">✕</span>`;
        return `<div class="strip-item${i === activeIdx ? " active" : ""}" data-i="${i}" title="${ABC.escapeHtml(im.name)}"><span class="strip-thumb">${thumb}${badge}</span><span class="strip-name">${ABC.escapeHtml(im.name)}</span>${del}</div>`;
      })
      .join("");
    if (countEl) countEl.textContent = `이미지 ${images.length}개`;
    // 실제 업로드 사진이 하나라도 있으면 '전체 AI 라벨링' 노출.
    if (batchBtn) batchBtn.hidden = !images.some((im) => im.file);
  };

  // 활성 이미지 전환 — 미리보기·박스·분석결과를 그 이미지 것으로 교체.
  const setActive = (i) => {
    if (i < 0 || i >= images.length) return;
    activeIdx = i;
    const im = images[i];
    imageName = im.name;
    imageURL = im.url;
    imageFile = im.file;
    savedBoxes = im.savedBoxes;
    if (im.url) {
      previewImg.src = im.url;
      previewImg.hidden = false;
      preview?.classList.add("has-image");
    } else {
      previewImg.removeAttribute("src");
      previewImg.hidden = true;
      preview?.classList.remove("has-image");
    }
    if (sampleName) sampleName.textContent = im.name;
    renderPreviewBoxes();
    restoreResult(im);
    renderStrip();
  };

  // 이미지 파일 판별 — MIME 타입이 비어 있는 경우(폴더 업로드 시 흔함)
  // 확장자로 폴백한다.
  const IMG_EXT = /\.(png|jpe?g|gif|webp|bmp|svg|avif|heic|heif|tiff?)$/i;
  const isImageFile = (f) => f.type.startsWith("image/") || IMG_EXT.test(f.name || "");

  // 이미지 추가(다중 파일/폴더). 첫 실제 업로드면 샘플 placeholder는 치운다.
  const addImages = (files) => {
    const imgs = [...files].filter(isImageFile);
    if (!imgs.length) {
      ABC.toast("이미지 파일이 없습니다 (선택한 폴더에 사진이 없어요)");
      return;
    }
    if (images.length === 1 && images[0].sample) images = [];
    imgs.forEach((f) =>
      images.push({
        name: f.name,
        url: URL.createObjectURL(f),
        file: f,
        sample: false,
        savedBoxes: [],
        result: null,
      }),
    );
    setActive(images.length - 1);
    ABC.toast(`사진 ${imgs.length}장을 추가했습니다`);
    openModal(); // 사진을 추가하면 바로 큰 캔버스에서 라벨링 시작(단계 축소)
  };

  // 이미지 제거. 모두 비면 샘플 placeholder로 복귀.
  const removeImage = (i) => {
    const im = images[i];
    if (!im || im.sample) return;
    if (im.url) URL.revokeObjectURL(im.url);
    images.splice(i, 1);
    if (!images.length) {
      images = [
        { name: SAMPLE_NAME, url: "", file: null, sample: true, savedBoxes: [], result: null },
      ];
    }
    setActive(Math.min(activeIdx, images.length - 1));
    ABC.toast("이미지를 제거했습니다");
  };

  // 포인터를 stage 기준 퍼센트로.
  const pct = (event) => {
    const r = boxesEl.getBoundingClientRect();
    return {
      x: (Math.min(Math.max(event.clientX - r.left, 0), r.width) / r.width) * 100,
      y: (Math.min(Math.max(event.clientY - r.top, 0), r.height) / r.height) * 100,
    };
  };

  let start = null;
  let temp = null;

  // 임시(드로잉 중) 박스를 항상 깔끔히 제거 — 누적/잔상 방지.
  const clearTemp = () => {
    boxesEl.querySelectorAll(".temp-box").forEach((el) => el.remove());
    temp = null;
  };

  stage.addEventListener("pointerdown", (event) => {
    const hit = event.target.closest(".draw-box");
    if (hit) {
      selected = Number(hit.dataset.i);
      render();
      return;
    }
    if (!imageURL) {
      ABC.toast("사진을 먼저 추가하세요");
      return; // 사진이 없으면 라벨(박스)을 그릴 수 없다
    }
    clearTemp(); // 이전 잔상 제거
    start = pct(event);
    stage.setPointerCapture(event.pointerId);
    temp = document.createElement("div");
    temp.className = "draw-box temp-box";
    boxesEl.appendChild(temp);
  });

  stage.addEventListener("pointermove", (event) => {
    if (!start || !temp) return;
    const p = pct(event);
    temp.style.left = `${Math.min(start.x, p.x)}%`;
    temp.style.top = `${Math.min(start.y, p.y)}%`;
    temp.style.width = `${Math.abs(p.x - start.x)}%`;
    temp.style.height = `${Math.abs(p.y - start.y)}%`;
  });

  const finishDraw = (event) => {
    if (!start) return;
    const p = pct(event);
    const x = Math.min(start.x, p.x);
    const y = Math.min(start.y, p.y);
    const w = Math.abs(p.x - start.x);
    const h = Math.abs(p.y - start.y);
    start = null;
    clearTemp();
    if (w >= 1.2 && h >= 1.2) {
      const label = (classInput.value || "object").trim() || "object";
      boxes.push({ x: +x.toFixed(2), y: +y.toFixed(2), w: +w.toFixed(2), h: +h.toFixed(2), label, confidence: null });
      selected = boxes.length - 1;
    }
    render(); // boxes 기준으로 재구성 → 임시 박스/잔상 없음
  };

  stage.addEventListener("pointerup", finishDraw);
  stage.addEventListener("pointercancel", () => {
    start = null;
    clearTemp();
    render();
  });

  listEl.addEventListener("input", (event) => {
    if (event.target.tagName !== "INPUT") return;
    const i = Number(event.target.closest("li").dataset.i);
    boxes[i].label = event.target.value;
    const tag = boxesEl.querySelector(`.draw-box[data-i="${i}"] .tag`);
    if (tag) tag.textContent = event.target.value + (boxes[i].confidence != null ? ` ${boxes[i].confidence}%` : "");
  });

  listEl.addEventListener("click", (event) => {
    const li = event.target.closest("li");
    if (!li) return;
    const i = Number(li.dataset.i);
    if (event.target.classList.contains("del")) {
      boxes.splice(i, 1);
      if (selected === i) selected = -1;
      render();
      ABC.toast("박스를 삭제했습니다");
    } else {
      selected = i;
      render();
    }
  });

  modal.querySelector(".modal-clear").addEventListener("click", () => {
    boxes = [];
    selected = -1;
    render();
    ABC.toast("박스를 모두 지웠습니다");
  });

  // 탐지 결과(labels) → 박스 배열. box_2d=[ymin,xmin,ymax,xmax] (0~1000 스케일).
  const labelsToBoxes = (result) =>
    (result.labels || [])
      .filter((l) => Array.isArray(l.box_2d) && l.box_2d.length === 4)
      .map((l) => {
        const [ymin, xmin, ymax, xmax] = l.box_2d;
        return {
          x: +(xmin / 10).toFixed(2),
          y: +(ymin / 10).toFixed(2),
          w: +((xmax - xmin) / 10).toFixed(2),
          h: +((ymax - ymin) / 10).toFixed(2),
          label: l.class_name || "object",
          tone: l.tone || "",
          confidence: typeof l.confidence === "number" ? l.confidence : null,
        };
      });

  // 한 이미지 탐지 호출 — 업로드 파일이 있으면 실제 YOLO(best.pt), 없으면 프리셋 MOCK.
  const detectImage = async (file, name) => {
    if (file) {
      const fd = new FormData();
      fd.append("image", file);
      const res = await fetch("/api/labeling/detect-image", { method: "POST", body: fd });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    }
    return ABC.api("/api/labeling/detect", { preset: "도로 파손/포트홀 찾기", image_name: name });
  };

  // AI 자동 탐지 — 현재 이미지에 박스 추가(같은 박스는 중복 추가하지 않는다).
  modal.querySelector(".modal-detect").addEventListener("click", async (event) => {
    if (!imageURL) return ABC.toast("사진을 먼저 추가하세요");
    const done = ABC.setBusy(event.currentTarget, "탐지 중");
    try {
      const result = await detectImage(imageFile, imageName);
      let added = 0;
      let dup = 0;
      labelsToBoxes(result).forEach((box) => {
        if (addBox(box)) added += 1;
        else dup += 1;
      });
      render();
      const engine = result.backend === "YOLO" ? "YOLO" : "MOCK";
      ABC.toast(
        added
          ? `${engine} 탐지: ${added}건 추가${dup ? `, 중복 ${dup}건 제외` : ""}`
          : dup
            ? "이미 추가된 박스입니다(중복 제외)"
            : "탐지된 객체가 없습니다",
      );
    } catch {
      ABC.toast("탐지에 실패했습니다");
    } finally {
      done();
    }
  });

  // ── 전체 객체 탐지 → 클래스 필터 → 선택한 것만 라벨 추가 ────────
  // 파손뿐 아니라 차량·보행자·표지판 등 모든 객체를 탐지해 대기 상태로 두고,
  // 클래스 칩(개수 표시)에서 체크한 클래스만 박스로 추가한다.
  const filterPanel = modal.querySelector(".detect-filter");
  const chipsEl = modal.querySelector(".filter-chips");
  let pendingBoxes = []; // 적용 대기 중인 탐지 결과

  const renderFilterChips = (isMock) => {
    const counts = {};
    pendingBoxes.forEach((b) => {
      counts[b.label] = (counts[b.label] || 0) + 1;
    });
    const note = isMock
      ? '<p class="filter-note">⚠ 지금은 예시 데이터입니다(탐지 모델·AI 한도 없음) — 실제 사진 위치와 무관합니다.</p>'
      : "";
    const rows = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(
        ([label, n]) =>
          `<label class="filter-row"><input type="checkbox" value="${ABC.escapeHtml(label)}" checked />` +
          `<span class="filter-name">${ABC.escapeHtml(label)}</span>` +
          `<span class="filter-count">${n}개</span></label>`,
      )
      .join("");
    chipsEl.innerHTML =
      note +
      '<label class="filter-row filter-all"><input type="checkbox" class="filter-check-all" checked />' +
      '<span class="filter-name">전체 선택</span></label>' +
      rows;
  };

  // 전체 선택 토글 (위임 — 필터 패널은 매번 다시 그려짐).
  chipsEl.addEventListener("change", (e) => {
    const boxes = () => [...chipsEl.querySelectorAll('input[type="checkbox"]:not(.filter-check-all)')];
    if (e.target.classList.contains("filter-check-all")) {
      boxes().forEach((cb) => (cb.checked = e.target.checked));
    } else {
      const all = chipsEl.querySelector(".filter-check-all");
      if (all) all.checked = boxes().every((cb) => cb.checked);
    }
  });

  modal.querySelector(".modal-detect-all").addEventListener("click", async (event) => {
    const done = ABC.setBusy(event.currentTarget, "탐지 중");
    try {
      let res;
      if (imageFile) {
        const fd = new FormData();
        fd.append("image", imageFile);
        res = await fetch("/api/labeling/detect-objects", { method: "POST", body: fd });
      } else {
        // 샘플(업로드 없음) → MOCK 객체로 필터 UI 시연.
        res = await fetch("/api/labeling/detect-objects", { method: "POST" });
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      pendingBoxes = labelsToBoxes(result);
      if (!pendingBoxes.length) {
        filterPanel.hidden = true;
        return ABC.toast("탐지된 객체가 없습니다");
      }
      const isMock = result.backend === "MOCK";
      renderFilterChips(isMock);
      filterPanel.hidden = false;
      const engine = result.backend === "YOLO" ? "YOLO 로컬" : result.backend === "GEMINI" ? "Gemini" : "예시(MOCK)";
      ABC.toast(`${engine} 탐지 ${pendingBoxes.length}개 — 추가할 클래스를 고르세요`);
    } catch {
      ABC.toast("전체 객체 탐지에 실패했습니다");
    } finally {
      done();
    }
  });

  modal.querySelector(".filter-cancel").addEventListener("click", () => {
    pendingBoxes = [];
    filterPanel.hidden = true;
  });

  modal.querySelector(".filter-apply").addEventListener("click", () => {
    const picked = new Set(
      [...chipsEl.querySelectorAll('input:checked:not(.filter-check-all)')].map((cb) => cb.value),
    );
    if (!picked.size) return ABC.toast("추가할 클래스를 선택하세요");
    let added = 0;
    let dup = 0;
    pendingBoxes.forEach((b) => {
      if (!picked.has(b.label)) return;
      if (addBox(b)) added += 1;
      else dup += 1;
    });
    pendingBoxes = [];
    filterPanel.hidden = true;
    render();
    ABC.logActivity("전체 객체 탐지", `${[...picked].join(", ")} · ${added}건`);
    ABC.toast(
      added
        ? `선택 객체 ${added}건 라벨 추가${dup ? ` (중복 ${dup}건 제외)` : ""}`
        : "이미 추가된 박스입니다(중복 제외)",
    );
  });

  // ── 내보내기 (프로토타입 labeling.py 와 동일 규약) ─────────────
  const imgSize = () => ({
    w: canvasImg.naturalWidth || 1000,
    h: canvasImg.naturalHeight || 1000,
  });
  const download = (filename, text, type = "text/plain") => {
    const blob = new Blob([text], { type: `${type};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };
  const baseName = () => imageName.replace(/\.[^.]+$/, "") || "labels";
  const classMap = () => {
    const names = [...new Set(boxes.map((b) => b.label))].sort();
    return Object.fromEntries(names.map((n, i) => [n, i]));
  };

  modal.querySelector(".modal-export-coco").addEventListener("click", () => {
    if (!boxes.length) return ABC.toast("내보낼 박스가 없습니다");
    const { w, h } = imgSize();
    const cmap = classMap();
    const coco = {
      images: [{ id: 1, file_name: imageName, width: w, height: h }],
      annotations: boxes.map((b, i) => {
        const px = (b.x / 100) * w;
        const py = (b.y / 100) * h;
        const bw = (b.w / 100) * w;
        const bh = (b.h / 100) * h;
        return { id: i + 1, image_id: 1, category_id: cmap[b.label], bbox: [+px.toFixed(2), +py.toFixed(2), +bw.toFixed(2), +bh.toFixed(2)], area: +(bw * bh).toFixed(2), iscrowd: 0 };
      }),
      categories: Object.entries(cmap).map(([name, id]) => ({ id, name })),
    };
    download(`${baseName()}.coco.json`, JSON.stringify(coco, null, 2), "application/json");
    ABC.toast("COCO JSON을 내려받았습니다");
  });

  modal.querySelector(".modal-export-yolo").addEventListener("click", () => {
    if (!boxes.length) return ABC.toast("내보낼 박스가 없습니다");
    const cmap = classMap();
    const lines = boxes.map((b) => {
      const cx = (b.x + b.w / 2) / 100;
      const cy = (b.y + b.h / 2) / 100;
      return `${cmap[b.label]} ${cx.toFixed(6)} ${cy.toFixed(6)} ${(b.w / 100).toFixed(6)} ${(b.h / 100).toFixed(6)}`;
    });
    download(`${baseName()}.txt`, lines.join("\n"));
    ABC.toast("YOLO txt를 내려받았습니다");
  });

  // 라벨 박스(+클래스명)를 그려 넣은 data URL 생성. 실제 이미지가 없으면(샘플)
  // 어두운 도로 배경을 그려 그 위에 박스를 얹는다 — 보고서에 라벨 결과를 넣기 위함.
  const makeLabeledThumb = (imgEl, boxList, max = 760) =>
    new Promise((resolve) => {
      const paint = (el) => {
        let W;
        let H;
        if (el && (el.naturalWidth || el.width)) {
          const iw = el.naturalWidth || el.width;
          const ih = el.naturalHeight || el.height;
          const scale = Math.min(1, max / Math.max(iw, ih));
          W = Math.round(iw * scale);
          H = Math.round(ih * scale);
        } else {
          el = null;
          W = max;
          H = Math.round(max * 0.6);
        }
        const c = document.createElement("canvas");
        c.width = W;
        c.height = H;
        const ctx = c.getContext("2d");
        try {
          if (el) {
            ctx.drawImage(el, 0, 0, W, H);
          } else {
            // 미리보기와 비슷한 어두운 도로 배경.
            const g = ctx.createLinearGradient(0, 0, 0, H);
            g.addColorStop(0, "#1f2b42");
            g.addColorStop(1, "#0c111c");
            ctx.fillStyle = g;
            ctx.fillRect(0, 0, W, H);
          }
          ctx.lineWidth = Math.max(2, Math.round(W / 280));
          const fs = Math.max(12, Math.round(W / 38));
          ctx.font = `700 ${fs}px sans-serif`;
          ctx.textBaseline = "top";
          boxList.forEach((b) => {
            const x = (b.x / 100) * W;
            const y = (b.y / 100) * H;
            const w = (b.w / 100) * W;
            const h = (b.h / 100) * H;
            ctx.strokeStyle = "#ef4444";
            ctx.strokeRect(x, y, w, h);
            const label = b.label || "object";
            const tw = ctx.measureText(label).width;
            const ly = Math.max(0, y - (fs + 6));
            ctx.fillStyle = "#ef4444";
            ctx.fillRect(x, ly, tw + 10, fs + 6);
            ctx.fillStyle = "#fff";
            ctx.fillText(label, x + 5, ly + 3);
          });
          resolve(c.toDataURL("image/jpeg", 0.85));
        } catch {
          resolve("");
        }
      };
      const src = imgEl instanceof HTMLImageElement ? imgEl.src : imgEl;
      if (imgEl instanceof HTMLImageElement && imgEl.complete && imgEl.naturalWidth) {
        paint(imgEl);
      } else if (src) {
        const e = new Image();
        e.onload = () => paint(e);
        e.onerror = () => paint(null); // 로드 실패 → placeholder
        e.src = src;
      } else {
        paint(null); // src 없음(샘플) → placeholder 위에 박스
      }
    });

  // 라벨 박스가 그려진 이미지 다운로드.
  modal.querySelector(".modal-export-img")?.addEventListener("click", async (event) => {
    if (!boxes.length) return ABC.toast("내보낼 박스가 없습니다");
    const done = ABC.setBusy(event.currentTarget, "생성 중");
    try {
      const url = await makeLabeledThumb(previewImg, boxes, 1600);
      if (!url) return ABC.toast("이미지를 만들지 못했습니다");
      const a = document.createElement("a");
      a.href = url;
      a.download = `${baseName()}_labeled.jpg`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      ABC.toast("라벨 이미지를 내려받았습니다");
    } finally {
      done();
    }
  });

  // 라벨 데이터셋에 저장 — 박스를 영속(미리보기 유지) + 백엔드 저장.
  const saveLabels = async (button) => {
    persist(); // 미리보기에 박스 반영(닫아도 유지)
    const done = ABC.setBusy(button, "저장 중");
    try {
      const result = await ABC.api("/api/labeling/save", {
        image_name: imageName,
        label_count: boxes.length,
      });
      ABC.logActivity("라벨 저장", `${imageName} (${boxes.length}개)`);
      // 보고서에 넣을 산출물로 저장(박스를 그려 넣은 라벨 이미지 + 라벨 결과).
      if (boxes.length) {
        const classes = [...new Set(boxes.map((b) => b.label))].filter(Boolean).join(", ");
        const thumb = await makeLabeledThumb(previewImg, boxes);
        if (thumb) {
          ABC.saveArtifact({
            kind: "image",
            id: imageName,
            title: `라벨링 · ${imageName}`,
            image: thumb,
            caption: `라벨 ${boxes.length}개${classes ? ` · ${classes}` : ""}`,
          });
        }
      }
      ABC.toast(`${result.message} — 미리보기에 반영됨`);
    } catch {
      /* api()가 toast */
    } finally {
      done();
    }
  };
  // 저장 안 한 변경이 있는지(저장본과 다름).
  const isDirty = () => JSON.stringify(boxes) !== JSON.stringify(savedBoxes);

  // "라벨 데이터셋에 저장" → 저장 후 모달 닫기.
  modal.querySelector(".modal-save").addEventListener("click", async (e) => {
    await saveLabels(e.currentTarget);
    modal.hidden = true;
  });

  // ── 저장 확인 다이얼로그 ────────────────────────────────────────
  const confirmEl = modal.querySelector(".confirm-save");
  modal.querySelector(".confirm-save-btn").addEventListener("click", async (e) => {
    confirmEl.hidden = true;
    await saveLabels(e.currentTarget);
    modal.hidden = true;
  });
  modal.querySelector(".confirm-discard").addEventListener("click", () => {
    confirmEl.hidden = true;
    boxes = clone(savedBoxes); // 변경 폐기(저장본으로 되돌림)
    render();
    modal.hidden = true;
  });
  modal.querySelector(".confirm-cancel").addEventListener("click", () => {
    confirmEl.hidden = true; // 닫지 않고 모달에 머무름
  });

  // ── 모달 내 사진 네비게이션(폴더 단위 라벨링) ──────────────────
  // 모달을 닫지 않고 폴더의 다른 사진으로 넘어가며 박스를 그린다.
  const updateModalNav = () => {
    const multi = images.length > 1;
    navEl.hidden = !multi;
    if (!multi) return;
    posEl.textContent = `${activeIdx + 1} / ${images.length}`;
    prevBtn.disabled = activeIdx === 0;
    nextBtn.disabled = activeIdx === images.length - 1;
  };

  // 현재 박스를 활성 이미지에 보관하고 이웃 사진으로 전환.
  const switchInModal = (dir) => {
    const next = activeIdx + dir;
    if (next < 0 || next >= images.length) return;
    persist(); // 현재 박스를 메모리에 저장 + 미리보기/갤러리 갱신(닫아도 유지)
    setActive(next); // 이미지명·미리보기·결과 패널 전환
    boxes = clone(savedBoxes); // 새 사진의 저장 박스를 편집 대상으로
    selected = -1;
    setImage(); // 캔버스 이미지·이름 갱신
    render();
    updateModalNav();
  };

  prevBtn.addEventListener("click", () => switchInModal(-1));
  nextBtn.addEventListener("click", () => switchInModal(1));

  // ── 모달 열기/닫기 ──────────────────────────────────────────────
  const openModal = () => {
    const s = ABC.getSettings();
    if (s.defaultClass) classInput.value = s.defaultClass;
    boxes = clone(savedBoxes); // 저장된 박스를 이어서 편집
    selected = -1;
    confirmEl.hidden = true;
    setImage();
    render();
    updateModalNav();
    modal.hidden = false;
  };
  const closeModal = () => {
    if (isDirty()) {
      confirmEl.hidden = false; // 저장할지 물어봄(자동 저장하지 않음)
      return;
    }
    modal.hidden = true;
  };

  document.querySelector(".open-label-modal")?.addEventListener("click", openModal);
  // 미리보기 클릭 = 큰 캔버스 열기(사진 없으면 추가부터) — 흐름 단순화.
  preview?.addEventListener("click", () => {
    if (!imageURL) return fileInput?.click();
    openModal();
  });
  modal.querySelector(".modal-close").addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (modal.hidden) return;
    if (event.key === "Escape") return closeModal();
    // 입력 중이 아닐 때만 ←/→ 로 사진 전환(폴더 라벨링).
    const typing = /^(INPUT|TEXTAREA)$/.test(event.target.tagName);
    if (!typing && event.key === "ArrowLeft") switchInModal(-1);
    if (!typing && event.key === "ArrowRight") switchInModal(1);
  });

  // ── 모드 탭 ─────────────────────────────────────────────────────
  document.querySelectorAll(".mode-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      ABC.activateInGroup(button, "button");
      if (button.textContent.includes("박스")) openModal();
    });
  });

  // ── 이미지 추가(다중 파일/폴더) + 갤러리 ────────────────────────
  document.querySelector(".add-images")?.addEventListener("click", () => fileInput?.click());
  document.querySelector(".add-folder")?.addEventListener("click", () => folderInput?.click());
  fileInput?.addEventListener("change", () => {
    if (fileInput.files?.length) addImages(fileInput.files);
    fileInput.value = ""; // 같은 파일 다시 선택 가능
  });
  folderInput?.addEventListener("change", () => {
    if (folderInput.files?.length) addImages(folderInput.files);
    folderInput.value = "";
  });
  // ── 폴더 전체 AI 라벨링 ─────────────────────────────────────────
  // 업로드한 모든 사진을 차례로 YOLO 탐지해 각 사진에 박스를 채운다(중복 제외).
  batchBtn?.addEventListener("click", async (event) => {
    const targets = images.filter((im) => im.file); // 실제 업로드 사진만(샘플 제외)
    if (!targets.length) return ABC.toast("폴더로 사진을 먼저 추가하세요");
    const restore = ABC.setBusy(event.currentTarget, "전체 라벨링 중");
    let ok = 0;
    let totalNew = 0;
    let failed = 0;
    for (let i = 0; i < targets.length; i += 1) {
      const im = targets[i];
      batchBtn.textContent = `라벨링 중 ${i + 1}/${targets.length}`;
      try {
        const result = await detectImage(im.file, im.name);
        const merged = im.savedBoxes.slice();
        labelsToBoxes(result).forEach((b) => {
          if (!merged.some((e) => sameBox(e, b))) {
            merged.push(b);
            totalNew += 1;
          }
        });
        im.savedBoxes = merged;
        ok += 1;
      } catch {
        failed += 1;
      }
    }
    savedBoxes = images[activeIdx].savedBoxes; // 활성 이미지 동기화(배열 교체됨)
    renderPreviewBoxes();
    renderStrip();
    ABC.logActivity("전체 AI 라벨링", `${ok}장 · 박스 ${totalNew}개`);
    restore();
    ABC.toast(
      failed
        ? `${ok}장 완료 · 박스 ${totalNew}개 (실패 ${failed}장)`
        : `${ok}장 전체 라벨링 완료 · 박스 ${totalNew}개`,
    );
  });

  // 갤러리 스트립: 항목 클릭 → 전환, ✕ → 제거.
  stripEl?.addEventListener("click", (e) => {
    const del = e.target.closest(".strip-del");
    if (del) {
      removeImage(Number(del.dataset.del));
      return;
    }
    const item = e.target.closest(".strip-item");
    if (item) setActive(Number(item.dataset.i));
  });

  // ── 설명 분석 (라디오 프리셋) ───────────────────────────────────
  document.querySelectorAll(".radio-list label").forEach((label) => {
    label.addEventListener("click", () => ABC.activateInGroup(label, "label"));
  });

  analyzeButton?.addEventListener("click", async () => {
    const preset =
      document.querySelector(".radio-list .active")?.textContent.trim() || "도로 파손/포트홀 찾기";
    const customPrompt = customInput?.value.trim() || "";
    const done = ABC.setBusy(analyzeButton, "분석 중");
    try {
      if (imageFile) {
        // 업로드 이미지가 있으면 실제 Gemini Vision으로 분석.
        const fd = new FormData();
        fd.append("image", imageFile);
        fd.append("preset", preset);
        fd.append("custom_prompt", customPrompt);
        const res = await fetch("/api/labeling/analyze-image", { method: "POST", body: fd });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        resultList.innerHTML = (result.description || "")
          .split(/\n+/)
          .filter(Boolean)
          .map((line) => `<li>${ABC.escapeHtml(line.replace(/^[-*•]\s*/, ""))}</li>`)
          .join("");
        confidence.textContent = result.backend === "GEMINI" ? "Gemini Vision" : "MOCK 분석";
        confidence.className = `status ${result.backend === "GEMINI" ? "green" : "gray"}`;
        // 보고서에 넣을 산출물로 저장(분석한 이미지 + 분석 요약).
        if (previewImg?.src) {
          const summary = (result.description || "")
            .split(/\n+/)
            .filter(Boolean)
            .slice(0, 2)
            .join(" / ")
            .slice(0, 160);
          // 저장된 라벨이 있으면 박스를 그려 넣은 이미지로(없으면 원본).
          const thumb = savedBoxes.length
            ? await makeLabeledThumb(previewImg, savedBoxes)
            : await ABC.toThumb(previewImg);
          if (thumb) {
            ABC.saveArtifact({
              kind: "image",
              id: imageName,
              title: `이미지 분석 · ${preset}`,
              image: thumb,
              caption: summary || preset,
            });
          }
        }
        ABC.toast(result.backend === "GEMINI" ? "이미지를 분석했습니다" : "분석 결과(MOCK)");
      } else {
        // 이미지 없으면 프리셋 기반 예시 결과(MOCK).
        const result = await ABC.api("/api/labeling/detect", {
          preset,
          custom_prompt: customPrompt,
          image_name: imageName,
        });
        resultList.innerHTML = result.labels
          .map((label) => {
            const text = label.class_name
              ? `<b>${ABC.escapeHtml(label.class_name)}</b> — ${ABC.escapeHtml(label.note)}`
              : ABC.escapeHtml(label.note);
            return `<li><span class="badge ${label.tone}">${ABC.escapeHtml(label.grade)}</span>${text}</li>`;
          })
          .join("");
        confidence.textContent = `예시(MOCK)`;
        confidence.className = "status gray";
        ABC.toast("사진을 추가하면 실제 분석합니다 (지금은 예시)");
      }
      saveCurResult(); // 분석 결과를 이 이미지에 저장(전환해도 유지)
      ABC.logActivity("이미지 분석", preset);
    } catch {
      ABC.toast("분석에 실패했습니다");
    } finally {
      done();
    }
  });

  // AI 대화 패널이 '이 페이지에 올린 이미지'를 근거로 답하도록 핸들러 등록.
  ABC.registerAskHandler(async (q) => {
    if (!imageFile) return "먼저 ‘교체’로 이미지를 올려주세요. 그 이미지를 보고 답해드립니다.";
    const fd = new FormData();
    fd.append("image", imageFile);
    fd.append("question", q);
    const res = await fetch("/api/ask/image", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()).answer;
  }, "이 페이지에 올린 이미지를 근거로 답합니다");

  // 샘플의 초기 분석 결과(정적 HTML)를 보관하고 갤러리를 처음 렌더.
  images[0].result = {
    html: resultList.innerHTML,
    confText: confidence.textContent,
    confClass: confidence.className,
  };
  renderStrip();
});
