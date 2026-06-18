"""YOLO-World 오픈보캐블 탐지기 (학습 없이 클래스명으로 탐지).

Gemini 대비 박스 위치(localization)가 대체로 정확하다. 단, '포트홀'처럼
흔치 않은 개념은 인식률이 들쭉날쭉할 수 있다(오픈보캐블 한계).

설계는 segmenter.py 와 동일: 무거운 import는 lazy, 실패하면 graceful degrade.
좌표/라벨 규약은 앱 전체와 통일: box_2d=[ymin,xmin,ymax,xmax] 0~1000, confidence 0~100.
"""

from __future__ import annotations

NORM = 1000.0

# YOLO-World는 영어 프롬프트가 안정적이라 한국어→영어 매핑을 둔다(없으면 원문 사용).
KO_EN = {
    "포트홀": "pothole",
    "균열": "crack",
    "맨홀": "manhole cover",
    "차량": "car",
    "자동차": "car",
    "사람": "person",
    "표지판": "traffic sign",
    "신호등": "traffic light",
    "도로 파손": "road damage",
}

_MODEL = None
_LOAD_ERROR: str | None = None


def is_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("ultralytics") is not None


def _load_model():
    global _MODEL, _LOAD_ERROR
    if _MODEL is not None or _LOAD_ERROR is not None:
        return _MODEL
    try:
        from ultralytics import YOLOWorld

        # 최초 1회 yolov8s-world.pt 자동 다운로드(~25MB).
        _MODEL = YOLOWorld("yolov8s-world.pt")
    except Exception as e:  # noqa: BLE001
        _LOAD_ERROR = str(e)
        _MODEL = None
    return _MODEL


def detect(image, targets: list[str], conf: float = 0.05) -> list[dict]:
    """targets(한국어 가능) 를 YOLO-World로 탐지해 라벨 목록 반환.

    실패(미설치/로드불가)는 RuntimeError 로 올린다(호출부에서 사용자 메시지로 변환).
    """
    if not targets:
        return []
    if not is_available():
        raise RuntimeError("ultralytics 미설치 — pip install ultralytics")
    model = _load_model()
    if model is None:
        raise RuntimeError(f"YOLO-World 로드 실패: {_LOAD_ERROR}")

    import numpy as np

    # 영어 프롬프트로 클래스 설정, 결과는 원래(한국어) 라벨로 되돌린다.
    en = [KO_EN.get(t, t) for t in targets]
    model.set_classes(en)

    rgb = image.convert("RGB")
    w, h = rgb.size
    arr = np.asarray(rgb)
    results = model.predict(arr, conf=conf, verbose=False)

    out = []
    if not results:
        return out
    for b in results[0].boxes:
        cls = int(b.cls[0])
        if cls < 0 or cls >= len(targets):
            continue
        x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
        box = [
            round(y1 / h * NORM), round(x1 / w * NORM),
            round(y2 / h * NORM), round(x2 / w * NORM),
        ]
        box = [max(0, min(int(NORM), v)) for v in box]
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        out.append({
            "class_name": targets[cls],  # 사용자 단어(한국어)로 통일.
            "box_2d": box,
            "confidence": int(round(float(b.conf[0]) * 100)),
        })
    return out
