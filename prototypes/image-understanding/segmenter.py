"""박스 → 정밀 마스크(폴리곤) 변환. MobileSAM(ultralytics) 사용, 없으면 graceful degrade.

흐름: Gemini가 준 바운딩 박스를 프롬프트로 SAM에 넣어 픽셀 단위 마스크를 얻고,
그 마스크의 외곽선을 폴리곤(0~1000 정규화 점들)으로 만들어 라벨에 붙인다.

설계:
- 무거운 import(torch/ultralytics/cv2)는 첫 사용 때 lazy 로드 → 평소 토큰/메모리 0.
- 모델/라이브러리가 없으면 마스크 없이 박스만 유지(앱이 깨지지 않음).
- 폴리곤 좌표 규약은 박스와 동일하게 0~1000 정규화로 통일.
"""

from __future__ import annotations

NORM = 1000.0

# lazy 캐시.
_MODEL = None
_LOAD_ERROR: str | None = None
# CPU에서 너무 큰 이미지는 SAM이 느리므로 긴 변을 이 픽셀로 제한해 추론.
_MAX_SIDE = 1024


def is_available() -> bool:
    """SAM을 실제로 쓸 수 있는지(라이브러리 import 가능 여부)."""
    import importlib.util

    return importlib.util.find_spec("ultralytics") is not None


def _load_model():
    """MobileSAM 모델을 한 번만 로드. 실패하면 _LOAD_ERROR에 사유 기록 후 None."""
    global _MODEL, _LOAD_ERROR
    if _MODEL is not None or _LOAD_ERROR is not None:
        return _MODEL
    try:
        from ultralytics import SAM

        # mobile_sam.pt 는 최초 1회 자동 다운로드(~40MB).
        _MODEL = SAM("mobile_sam.pt")
    except Exception as e:  # noqa: BLE001 - 어떤 이유든 마스크 없이 계속 가야 함.
        _LOAD_ERROR = str(e)
        _MODEL = None
    return _MODEL


def _mask_to_polygon(mask, w: int, h: int, eps_ratio: float = 0.005):
    """이진 마스크(bool/0~1 ndarray) → 0~1000 정규화 폴리곤 점 리스트.

    가장 큰 외곽선 하나만 사용(노이즈 제거). 점이 너무 적으면 None.
    """
    import cv2
    import numpy as np

    m = (np.asarray(mask) > 0.5).astype("uint8")
    if m.sum() == 0:
        return None
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, eps_ratio * peri, True)  # 점 수 단순화.
    pts = approx.reshape(-1, 2)
    if len(pts) < 3:
        return None
    # 픽셀 → 0~1000 정규화.
    poly = []
    for x, y in pts:
        poly.append([round(float(x) / w * NORM, 1), round(float(y) / h * NORM, 1)])
    return poly


def segment_labels(image, labels: list[dict]) -> tuple[list[dict], str]:
    """각 라벨 박스를 SAM으로 정밀화해 'polygon'(0~1000)을 추가한 새 라벨 목록 반환.

    Returns:
        (새 라벨 목록, 상태 메시지). 라벨은 원본을 복사 후 polygon 키만 추가한다.
        모델이 없거나 실패하면 원본 라벨을 그대로 돌려준다(polygon 없음).
    """
    if not labels:
        return labels, "라벨이 없습니다."
    if not is_available():
        return labels, "SAM 미설치 — 박스만 유지(정밀 마스크 없음). `pip install ultralytics opencv-python`"

    model = _load_model()
    if model is None:
        return labels, f"SAM 로드 실패 — 박스만 유지. ({_LOAD_ERROR})"

    import numpy as np

    rgb = image.convert("RGB")
    w0, h0 = rgb.size
    # CPU 추론 가속: 긴 변을 _MAX_SIDE 로 축소(좌표는 정규화라 복원 불필요).
    scale = min(1.0, _MAX_SIDE / max(w0, h0))
    if scale < 1.0:
        small = rgb.resize((max(1, int(w0 * scale)), max(1, int(h0 * scale))))
    else:
        small = rgb
    w, h = small.size
    arr = np.asarray(small)

    # 0~1000 정규화 박스 → 축소 이미지 픽셀 박스(xyxy).
    bboxes = []
    for lb in labels:
        ymin, xmin, ymax, xmax = lb["box_2d"]
        bboxes.append([xmin / NORM * w, ymin / NORM * h, xmax / NORM * w, ymax / NORM * h])

    try:
        results = model(arr, bboxes=bboxes, verbose=False)
    except Exception as e:  # noqa: BLE001
        return labels, f"SAM 추론 실패 — 박스만 유지. ({e})"

    out = []
    masked = 0
    masks = getattr(results[0], "masks", None) if results else None
    mask_data = masks.data.cpu().numpy() if masks is not None else None

    for i, lb in enumerate(labels):
        new = dict(lb)
        if mask_data is not None and i < len(mask_data):
            poly = _mask_to_polygon(mask_data[i], w, h)
            if poly:
                new["polygon"] = poly
                masked += 1
        out.append(new)

    msg = f"정밀 마스크 {masked}/{len(labels)}개 생성." if masked else "마스크를 만들지 못했습니다(박스 유지)."
    return out, msg
