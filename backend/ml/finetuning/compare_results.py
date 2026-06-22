import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = BACKEND_ROOT / "storage" / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare base and fine-tuned YOLO predictions.")
    parser.add_argument("--base-model", required=True, help="Base model name or local .pt path.")
    parser.add_argument("--fine-tuned-model", required=True, help="Fine-tuned local .pt path.")
    parser.add_argument("--image", required=True, help="Image path.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--output", help="Optional JSON output path.")
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


def run_prediction(model_ref: str, image_path: Path, conf: float) -> dict:
    from ultralytics import YOLO

    model = YOLO(model_ref)
    results = model.predict(source=str(image_path), conf=conf, verbose=False)
    return {
        "model": model_ref,
        "detections": detections_from_results(results, Path(model_ref).name),
    }


def count_by_label(detections: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for detection in detections:
        label = str(detection["label"])
        counts[label] = counts.get(label, 0) + 1
    return counts


def main() -> None:
    args = parse_args()
    image_path = Path(args.image).expanduser()
    if not image_path.is_file():
        raise SystemExit(f"Image not found: {image_path}")

    try:
        import ultralytics  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "ultralytics is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    output = {
        "image": str(image_path),
        "confidence_threshold": args.conf,
        "base": run_prediction(args.base_model, image_path, args.conf),
        "fine_tuned": run_prediction(args.fine_tuned_model, image_path, args.conf),
    }
    output["summary"] = {
        "base_count": len(output["base"]["detections"]),
        "fine_tuned_count": len(output["fine_tuned"]["detections"]),
        "base_labels": count_by_label(output["base"]["detections"]),
        "fine_tuned_labels": count_by_label(output["fine_tuned"]["detections"]),
    }

    if args.output:
        output_path = Path(args.output).expanduser()
    else:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_path = DEFAULT_OUTPUT_DIR / f"comparison_{timestamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(json.dumps(output, indent=2))
    print(f"Saved comparison: {output_path}")


if __name__ == "__main__":
    main()
