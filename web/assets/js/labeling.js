document.addEventListener("DOMContentLoaded", () => {
  const analyzeButton = document.querySelector(".label-panel .primary");
  const resultList = document.querySelector(".finding-list");
  const confidence = document.querySelector(".result-card .status");
  const customInput = document.querySelector(".label-panel textarea");

  const fileInput = document.querySelector(".image-input");
  const previewImg = document.querySelector(".preview-img");
  const preview = document.querySelector(".road-preview");
  const sampleName = document.querySelector(".sample-name");
  let imageName = sampleName?.textContent.trim() || "";

  // ── 박스 그리기 모드 ─────────────────────────────────────────────
  const boxLayer = document.querySelector(".box-layer");
  const toolbar = document.querySelector(".draw-toolbar");
  const classInput = document.querySelector(".box-class");
  const boxCount = document.querySelector(".box-count");
  const clearButton = document.querySelector(".clear-boxes");
  const boxes = []; // {x, y, w, h, label} (퍼센트)

  const isBoxTab = (button) => button.textContent.includes("박스");

  const setMode = (boxMode) => {
    preview?.classList.toggle("draw-mode", boxMode);
    if (toolbar) toolbar.hidden = !boxMode;
  };

  const updateCount = () => {
    if (boxCount) boxCount.textContent = `박스 ${boxes.length}개`;
  };

  document.querySelectorAll(".mode-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      ABC.activateInGroup(button, "button");
      setMode(isBoxTab(button));
    });
  });

  // 드래그로 박스 그리기
  let start = null;
  let tempBox = null;

  const relPos = (event) => {
    const rect = boxLayer.getBoundingClientRect();
    const x = Math.min(Math.max(event.clientX - rect.left, 0), rect.width);
    const y = Math.min(Math.max(event.clientY - rect.top, 0), rect.height);
    return { x, y, w: rect.width, h: rect.height };
  };

  boxLayer?.addEventListener("pointerdown", (event) => {
    if (!preview.classList.contains("draw-mode")) return;
    start = relPos(event);
    boxLayer.setPointerCapture(event.pointerId);
    tempBox = document.createElement("div");
    tempBox.className = "draw-box";
    boxLayer.appendChild(tempBox);
  });

  boxLayer?.addEventListener("pointermove", (event) => {
    if (!start || !tempBox) return;
    const p = relPos(event);
    const left = Math.min(start.x, p.x);
    const top = Math.min(start.y, p.y);
    const w = Math.abs(p.x - start.x);
    const h = Math.abs(p.y - start.y);
    Object.assign(tempBox.style, {
      left: `${left}px`,
      top: `${top}px`,
      width: `${w}px`,
      height: `${h}px`,
    });
  });

  const finishBox = (event) => {
    if (!start || !tempBox) return;
    const p = relPos(event);
    const left = Math.min(start.x, p.x);
    const top = Math.min(start.y, p.y);
    const w = Math.abs(p.x - start.x);
    const h = Math.abs(p.y - start.y);
    start = null;

    // 너무 작은 박스는 취소(클릭 오작동 방지).
    if (w < 8 || h < 8) {
      tempBox.remove();
      tempBox = null;
      return;
    }

    const label = (classInput?.value || "object").trim() || "object";
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = label;
    tempBox.appendChild(tag);

    boxes.push({
      x: +((left / p.w) * 100).toFixed(1),
      y: +((top / p.h) * 100).toFixed(1),
      w: +((w / p.w) * 100).toFixed(1),
      h: +((h / p.h) * 100).toFixed(1),
      label,
    });
    tempBox = null;
    updateCount();
    ABC.toast(`‘${label}’ 박스를 추가했습니다`);
  };

  boxLayer?.addEventListener("pointerup", finishBox);

  clearButton?.addEventListener("click", () => {
    boxes.length = 0;
    boxLayer.querySelectorAll(".draw-box").forEach((box) => box.remove());
    updateCount();
    ABC.toast("박스를 모두 지웠습니다");
  });

  // ── 이미지 업로드/교체 ──────────────────────────────────────────
  document.querySelector(".replace-image")?.addEventListener("click", (event) => {
    event.preventDefault();
    fileInput?.click();
  });

  fileInput?.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;
    if (previewImg.src) URL.revokeObjectURL(previewImg.src);
    previewImg.src = URL.createObjectURL(file);
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

  // ── 결과 액션: "박스로 찾기" / "라벨로 저장" ─────────────────────
  document.querySelectorAll(".result-card .answer-actions button").forEach((button) => {
    const label = button.textContent.trim();
    if (label.includes("박스")) {
      button.addEventListener("click", () => {
        const boxTab = [...document.querySelectorAll(".mode-tabs button")].find(isBoxTab);
        if (boxTab) ABC.activateInGroup(boxTab, "button");
        setMode(true);
        preview?.scrollIntoView({ behavior: "smooth", block: "center" });
        ABC.toast("박스 그리기 모드 — 이미지 위를 드래그하세요");
      });
    } else if (label.includes("저장")) {
      button.addEventListener("click", async () => {
        // 그린 박스가 있으면 그 개수를, 없으면 분석 결과 개수를 저장.
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
