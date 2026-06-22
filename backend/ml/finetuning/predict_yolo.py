import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run YOLO prediction on one image.")
    parser.add_argument("--model", required=True, help="Model name or local .pt path.")
    parser.add_argument("--image", required=True, help="Image path.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    return parser.parse_args()


def detections_from_results(results: Any, model_name: str) -> list[dict]:
    detections: list[dict] = []
    for result in results:
        names = getattr(result, "names", None) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue

        for box in boxes:
            class_id = int(box.cls[0].detach().cpu())
            detections.append(
                {
                    "label": str(names.get(class_id, class_id)),
                    "confidence": round(float(box.conf[0].detach().cpu()), 4),
                    "bbox": [
                        round(float(value), 2) for value in box.xyxy[0].detach().cpu().tolist()
                    ],
                    "source": f"yolo:{model_name}",
                }
            )
    return detections


def main() -> None:
    args = parse_args()
    image_path = Path(args.image).expanduser()
    if not image_path.is_file():
        raise SystemExit(f"Image not found: {image_path}")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "ultralytics is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    model = YOLO(args.model)
    results = model.predict(source=str(image_path), conf=args.conf, verbose=False)
    output = {
        "image": str(image_path),
        "model": args.model,
        "detections": detections_from_results(results, Path(args.model).name),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
