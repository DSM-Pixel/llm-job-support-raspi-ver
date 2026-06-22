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
