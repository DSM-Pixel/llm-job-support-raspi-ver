"""YOLO 도로파손 탐지 서비스.

geunyoung0120/abc_project_geunyoung 백엔드의 YoloService 를 이 프로젝트 구조에
맞게 리팩토링해 가져왔다. 학습 모델(best.pt, 클래스: pothole/crack/road_damage)로
업로드 이미지에서 실제 박스를 탐지한다. 모델/라이브러리가 없으면 MOCK 으로 폴백한다.

좌표 규약은 프론트(라벨링 모달)와 동일하게 0~1000 정규화 [ymin, xmin, ymax, xmax].
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

_MODEL_PATH = Path(__file__).resolve().parent / "storage" / "models" / "best.pt"

# 모델 클래스(영문) → 한글 표시명 + 등급/색.
_CLASS_MAP = {
    "pothole": {"name": "포트홀", "grade": "상", "tone": "red"},
    "crack": {"name": "균열", "grade": "중", "tone": "orange"},
    "road_damage": {"name": "도로파손", "grade": "중", "tone": "orange"},
}


@lru_cache(maxsize=1)
def _load_model():
    """best.pt 를 한 번만 로드(캐시). 실패 시 None."""
    if not _MODEL_PATH.is_file():
        return None
    try:
        from ultralytics import YOLO

        return YOLO(str(_MODEL_PATH))
    except Exception:
        return None


def model_available() -> bool:
    return _load_model() is not None


# ── 일반 객체 모델(yolov8n, COCO 80클래스) — '전체 객체 탐지'용 ──────
# VLM(Gemini)의 부정확한 박스 좌표·API 한도 문제를 피하기 위해 로컬에서
# 사람·차량·신호등 등 일반 객체를 픽셀 정확도로 탐지한다.
_GENERAL_MODEL_PATH = Path(__file__).resolve().parent / "storage" / "models" / "yolov8n.pt"

# COCO 클래스(영문) → 한글 표시명. 도로 장면에서 나올 법한 것 위주.
_COCO_KO = {
    "person": "사람",
    "bicycle": "자전거",
    "car": "차량",
    "motorcycle": "오토바이",
    "bus": "버스",
    "truck": "트럭",
    "train": "기차",
    "traffic light": "신호등",
    "stop sign": "표지판",
    "fire hydrant": "소화전",
    "bench": "벤치",
    "dog": "개",
    "cat": "고양이",
    "bird": "새",
    "umbrella": "우산",
    "backpack": "가방",
    "potted plant": "화분",
}

# 클래스별 표시 톤 — 파손=경고색, 사람=빨강, 이동체=파랑, 시설물=초록.
_GENERAL_TONES = {
    "사람": "red",
    "차량": "blue",
    "트럭": "blue",
    "버스": "blue",
    "오토바이": "blue",
    "자전거": "blue",
    "기차": "blue",
    "신호등": "green",
    "표지판": "green",
    "소화전": "green",
    "벤치": "green",
}


@lru_cache(maxsize=1)
def _load_general_model():
    """yolov8n(일반 객체)을 한 번만 로드(캐시). 없거나 실패 시 None."""
    if not _GENERAL_MODEL_PATH.is_file():
        return None
    try:
        from ultralytics import YOLO

        return YOLO(str(_GENERAL_MODEL_PATH))
    except Exception:
        return None


def _predict_labels(model, image, w: int, h: int, conf: float, class_map) -> list[dict]:
    """모델 1개 추론 → 공통 라벨 스키마 목록. class_map(raw)-> (name, grade, tone)."""
    labels: list[dict] = []
    try:
        results = model.predict(source=image, conf=conf, verbose=False)
    except Exception:
        return labels
    for result in results:
        names = getattr(result, "names", None) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            confidence = round(float(box.conf[0]) * 100)
            raw = str(names.get(int(box.cls[0]), int(box.cls[0])))
            name, grade, tone = class_map(raw)
            labels.append(
                {
                    "class_name": name,
                    "grade": grade,
                    "tone": tone,
                    "note": f"YOLO 로컬 탐지 · 신뢰도 {confidence}%",
                    "box_2d": _to_box_2d(x1, y1, x2, y2, w, h),
                    "confidence": confidence,
                }
            )
    return labels


def detect_all_boxes(image_bytes: bytes, conf: float = 0.3) -> dict | None:
    """'전체 객체 탐지' — 파손(best.pt) + 일반 객체(yolov8n)를 로컬에서 함께 탐지.

    둘 다 없으면 None(호출부가 Gemini/MOCK 폴백). 좌표는 픽셀 기반이라 정확하다.
    """
    import io as _io

    from PIL import Image

    damage = _load_model()
    general = _load_general_model()
    if damage is None and general is None:
        return None

    image = Image.open(_io.BytesIO(image_bytes)).convert("RGB")
    w, h = image.size
    labels: list[dict] = []
    engines: list[str] = []

    if damage is not None:  # 포트홀·균열·도로파손 (파인튜닝 모델)

        def _dmg(raw: str):
            meta = _CLASS_MAP.get(raw, {"name": raw, "grade": "중", "tone": "orange"})
            return meta["name"], meta["grade"], meta["tone"]

        labels += _predict_labels(damage, image, w, h, max(conf, 0.25), _dmg)
        engines.append("best.pt")

    if general is not None:  # 사람·차량·신호등 등 일반 객체 (COCO)

        def _gen(raw: str):
            name = _COCO_KO.get(raw, raw)
            return name, "객체", _GENERAL_TONES.get(name, "gray")

        labels += _predict_labels(general, image, w, h, conf, _gen)
        engines.append("yolov8n")

    return {"backend": "YOLO", "engine": "+".join(engines), "labels": labels}


def _to_box_2d(x1: float, y1: float, x2: float, y2: float, w: int, h: int) -> list[int]:
    """픽셀 xyxy → 0~1000 정규화 [ymin, xmin, ymax, xmax]."""
    return [
        max(0, min(1000, round(y1 / h * 1000))),
        max(0, min(1000, round(x1 / w * 1000))),
        max(0, min(1000, round(y2 / h * 1000))),
        max(0, min(1000, round(x2 / w * 1000))),
    ]


def detect_boxes(image_bytes: bytes, conf: float = 0.25) -> dict:
    """이미지 바이트에서 박스를 탐지해 라벨 목록으로 반환.

    반환: {"backend","engine","labels":[{class_name,grade,tone,note,box_2d,confidence}]}
    """
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = image.size
    model = _load_model()

    if model is None:
        return {"backend": "MOCK", "engine": "mock", "labels": _mock_labels()}

    try:
        results = model.predict(source=image, conf=conf, verbose=False)
    except Exception:
        return {"backend": "MOCK", "engine": "mock", "labels": _mock_labels()}

    labels: list[dict] = []
    for result in results:
        names = getattr(result, "names", None) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            confidence = round(float(box.conf[0]) * 100)
            cls_id = int(box.cls[0])
            raw = str(names.get(cls_id, cls_id))
            meta = _CLASS_MAP.get(raw, {"name": raw, "grade": "중", "tone": "orange"})
            labels.append(
                {
                    "class_name": meta["name"],
                    "grade": meta["grade"],
                    "tone": meta["tone"],
                    "note": f"YOLO 자동 탐지 · 신뢰도 {confidence}%",
                    "box_2d": _to_box_2d(x1, y1, x2, y2, w, h),
                    "confidence": confidence,
                }
            )

    return {"backend": "YOLO", "engine": "best.pt", "labels": labels}


def _mock_labels() -> list[dict]:
    """모델/라이브러리 부재 시 폴백(고정 박스)."""
    return [
        {
            "class_name": "포트홀",
            "grade": "상",
            "tone": "red",
            "note": "MOCK 탐지(모델 없음)",
            "box_2d": [610, 80, 880, 360],
            "confidence": 87,
        },
    ]
