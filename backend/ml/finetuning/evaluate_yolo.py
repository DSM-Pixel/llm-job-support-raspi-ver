import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an Ultralytics YOLO model.")
    parser.add_argument("--model", required=True, help="Model name or local .pt path.")
    parser.add_argument("--data", required=True, help="Path to YOLO data.yaml.")
    parser.add_argument("--imgsz", type=int, default=640, help="Validation image size.")
    parser.add_argument("--batch", type=int, default=16, help="Validation batch size.")
    return parser.parse_args()


def metrics_to_dict(metrics: Any) -> dict:
    if hasattr(metrics, "results_dict"):
        return dict(metrics.results_dict)
    if isinstance(metrics, dict):
        return metrics
    return {"raw": str(metrics)}


def main() -> None:
    args = parse_args()
    data_path = Path(args.data).expanduser()
    if not data_path.is_file():
        raise SystemExit(f"Dataset config not found: {data_path}")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "ultralytics is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    model = YOLO(args.model)
    metrics = model.val(data=str(data_path), imgsz=args.imgsz, batch=args.batch)
    output = {
        "model": args.model,
        "data": str(data_path),
        "metrics": metrics_to_dict(metrics),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
