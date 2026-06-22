document.addEventListener("DOMContentLoaded", () => {
  const analyzeButton = document.querySelector(".label-panel .primary");
  const resultList = document.querySelector(".finding-list");
  const confidence = document.querySelector(".result-card .status");
  const customInput = document.querySelector(".label-panel textarea");

  const fileInput = document.querySelector(".image-input");
  const previewImg = document.querySelector(".preview-img");
  const preview = document.querySelector(".road-preview");
  const sampleName = document.querySelector(".sample-name");

  let imageName = sampleName?.textContent.trim() || "image.png";
  let imageURL = ""; // 업로드된 이미지의 object URL (없으면 빈 문자열)

  // ════════════════════════════════════════════════════════════════
  //  라벨링 모달 — 큰 이미지 위에서 박스 그리기/편집/삭제
  // ════════════════════════════════════════════════════════════════
  const modal = document.querySelector("#label-modal");
  const stage = modal.querySelector(".canvas-stage");
  const canvasImg = modal.querySelector(".canvas-img");
  const boxesEl = modal.querySelector(".canvas-boxes");
  const listEl = modal.querySelector(".box-list");
  const classInput = modal.querySelector(".modal-class");
  const confSlider = modal.querySelector(".modal-conf");
  const confVal = modal.querySelector(".conf-val");
  const totalEl = modal.querySelector(".box-total");
  const nameEl = modal.querySelector(".modal-imgname");

  let boxes = []; // {x,y,w,h (%, 0~100), label, confidence|null}
  let selected = -1;

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

  // confidence 필터를 통과하는지 (값 없으면 통과)
  const passesConf = (box) => {
    const min = Number(confSlider.value) || 0;
    return box.confidence == null || box.confidence >= min;
  };

  const render = () => {
    const visible = boxes.filter(passesConf);
    boxesEl.innerHTML = visible
      .map((b) => {
        const i = boxes.indexOf(b);
        return `<div class="draw-box${i === selected ? " selected" : ""}" data-i="${i}" style="left:${b.x}%;top:${b.y}%;width:${b.w}%;height:${b.h}%"><span class="tag">${ABC.escapeHtml(b.label)}${b.confidence != null ? ` ${b.confidence}%` : ""}</span></div>`;
      })
      .join("");
    listEl.innerHTML = visible
      .map((b) => {
        const i = boxes.indexOf(b);
        return `<li class="${i === selected ? "selected" : ""}" data-i="${i}"><input value="${ABC.escapeHtml(b.label)}" /><span class="conf">${b.confidence != null ? `${b.confidence}%` : "—"}</span><button class="del" type="button" aria-label="삭제">✕</button></li>`;
      })
      .join("");
    totalEl.textContent = String(visible.length);
  };

  // 박스 좌표(%) 계산용 — 포인터를 stage 기준 퍼센트로.
  const pct = (event) => {
    const r = boxesEl.getBoundingClientRect();
    return {
      x: (Math.min(Math.max(event.clientX - r.left, 0), r.width) / r.width) * 100,
      y: (Math.min(Math.max(event.clientY - r.top, 0), r.height) / r.height) * 100,
      w: r.width,
      h: r.height,
    };
  };

  let start = null;
  let temp = null;

  stage.addEventListener("pointerdown", (event) => {
    // 기존 박스를 누르면 선택, 빈 영역이면 새로 그리기.
    const hit = event.target.closest(".draw-box");
    if (hit) {
      selected = Number(hit.dataset.i);
      render();
      return;
    }
    start = pct(event);
    stage.setPointerCapture(event.pointerId);
    temp = document.createElement("div");
    temp.className = "draw-box";
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

  stage.addEventListener("pointerup", (event) => {
    if (!start || !temp) return;
    const p = pct(event);
    const x = Math.min(start.x, p.x);
    const y = Math.min(start.y, p.y);
    const w = Math.abs(p.x - start.x);
    const h = Math.abs(p.y - start.y);
    temp.remove();
    temp = null;
    start = null;
    // 너무 작은 박스(오클릭)는 무시 — stage 기준 약 1% 미만.
    if (w < 1.2 || h < 1.2) return;
    const label = (classInput.value || "object").trim() || "object";
    boxes.push({ x: +x.toFixed(2), y: +y.toFixed(2), w: +w.toFixed(2), h: +h.toFixed(2), label, confidence: null });
    selected = boxes.length - 1;
    render();
    ABC.toast(`‘${label}’ 박스 추가`);
  });

  // 목록: 클래스명 수정 / 삭제 / 선택
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

  confSlider.addEventListener("input", () => {
    confVal.textContent = `${confSlider.value}%`;
    render();
  });

  modal.querySelector(".modal-clear").addEventListener("click", () => {
    boxes = [];
    selected = -1;
    render();
    ABC.toast("박스를 모두 지웠습니다");
  });

  // AI 자동 탐지 → box_2d(0~1000)를 퍼센트로 변환해 추가
  modal.querySelector(".modal-detect").addEventListener("click", async (event) => {
    const done = ABC.setBusy(event.currentTarget, "탐지 중");
    try {
      const result = await ABC.api("/api/labeling/detect", {
        preset: "도로 파손/포트홀 찾기",
        image_name: imageName,
      });
      result.labels
        .filter((l) => Array.isArray(l.box_2d) && l.box_2d.length === 4)
        .forEach((l) => {
          const [ymin, xmin, ymax, xmax] = l.box_2d;
          boxes.push({
            x: +(xmin / 10).toFixed(2),
            y: +(ymin / 10).toFixed(2),
            w: +((xmax - xmin) / 10).toFixed(2),
            h: +((ymax - ymin) / 10).toFixed(2),
            label: l.class_name || "object",
            confidence: typeof l.confidence === "number" ? l.confidence : null,
          });
        });
      render();
      ABC.toast("AI 탐지 결과를 추가했습니다");
    } catch {
      /* handled */
    } finally {
      done();
    }
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

  const baseName = () => (imageName.replace(/\.[^.]+$/, "") || "labels");

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
        return {
          id: i + 1,
          image_id: 1,
          category_id: cmap[b.label],
          bbox: [+px.toFixed(2), +py.toFixed(2), +bw.toFixed(2), +bh.toFixed(2)],
          area: +(bw * bh).toFixed(2),
          iscrowd: 0,
        };
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

  modal.querySelector(".modal-save").addEventListener("click", async (event) => {
    const done = ABC.setBusy(event.currentTarget, "저장 중");
    try {
      const result = await ABC.api("/api/labeling/save", {
        image_name: imageName,
        label_count: boxes.length,
      });
      ABC.toast(result.message);
    } catch {
      /* handled */
    } finally {
      done();
    }
  });

  // ── 모달 열기/닫기 ──────────────────────────────────────────────
  const openModal = () => {
    // 설정(⚙)의 기본 클래스명·신뢰도 임계값을 반영.
    const s = ABC.getSettings();
    if (s.defaultClass) classInput.value = s.defaultClass;
    confSlider.value = s.minConf || 0;
    confVal.textContent = `${confSlider.value}%`;
    setImage();
    render();
    modal.hidden = false;
  };
  const closeModal = () => {
    modal.hidden = true;
  };

  document.querySelector(".open-label-modal")?.addEventListener("click", openModal);
  modal.querySelector(".modal-close").addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeModal();
  });

  // ── 모드 탭 ─────────────────────────────────────────────────────
  document.querySelectorAll(".mode-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      ABC.activateInGroup(button, "button");
      if (button.textContent.includes("박스")) openModal();
    });
  });

  // ── 이미지 업로드/교체 (인라인 미리보기 + 모달 공용) ────────────
  document.querySelector(".replace-image")?.addEventListener("click", (event) => {
    event.preventDefault();
    fileInput?.click();
  });

  fileInput?.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;
    if (imageURL) URL.revokeObjectURL(imageURL);
    imageURL = URL.createObjectURL(file);
    previewImg.src = imageURL;
    previewImg.hidden = false;
    preview?.classList.add("has-image");
    imageName = file.name;
    if (sampleName) sampleName.textContent = file.name;
    ABC.toast("이미지를 교체했습니다");
  });

  // ── 설명 분석 (라디오 프리셋) ───────────────────────────────────
  document.querySelectorAll(".radio-list label").forEach((label) => {
    label.addEventListener("click", () => ABC.activateInGroup(label, "label"));
  });

  let labelCount = resultList ? resultList.querySelectorAll("li").length : 0;

  analyzeButton?.addEventListener("click", async () => {
    const preset =
      document.querySelector(".radio-list .active")?.textContent.trim() ||
      "도로 파손/포트홀 찾기";
    const customPrompt = customInput?.value.trim() || "";

    const done = ABC.setBusy(analyzeButton, "분석 중");
    try {
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
      labelCount = result.labels.length;
      confidence.textContent = `신뢰도 ${result.confidence.toFixed(2)}`;
      ABC.toast("이미지 분석이 완료되었습니다");
    } catch {
      /* api()가 toast 표시 */
    } finally {
      done();
    }
  });

  // ── 결과 액션: "박스로 찾기"(모달) / "라벨로 저장" ──────────────
  document.querySelectorAll(".result-card .answer-actions button").forEach((button) => {
    const label = button.textContent.trim();
    if (label.includes("박스")) {
      button.addEventListener("click", openModal);
    } else if (label.includes("저장")) {
      button.addEventListener("click", async () => {
        const count = boxes.length || labelCount;
        const done = ABC.setBusy(button, "저장 중");
        try {
          const result = await ABC.api("/api/labeling/save", {
            image_name: imageName,
            label_count: count,
          });
          ABC.toast(result.message);
        } catch {
          /* handled */
        } finally {
          done();
        }
      });
    }
  });
});
