import argparse
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROJECT = BACKEND_ROOT / "storage" / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train an Ultralytics YOLO model.")
    parser.add_argument("--data", required=True, help="Path to YOLO data.yaml.")
    parser.add_argument("--model", default="yolo11n.pt", help="Base model name or local .pt path.")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs.")
    parser.add_argument("--imgsz", type=int, default=640, help="Training image size.")
    parser.add_argument(
        "--batch", type=int, default=16, help="Training batch size. Use -1 for auto batch."
    )
    parser.add_argument("--project", default=str(DEFAULT_PROJECT), help="Output project directory.")
    parser.add_argument(
        "--name", default="road_damage_yolo", help="Run name under the project directory."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = Path(args.data).expanduser()
    project_path = Path(args.project).expanduser().resolve()
    project_path.mkdir(parents=True, exist_ok=True)

    if not data_path.is_file():
        raise SystemExit(f"Dataset config not found: {data_path}")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "ultralytics is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    model = YOLO(args.model)
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(project_path),
        name=args.name,
    )

    weights_dir = project_path / args.name / "weights"
    best_weights = weights_dir / "best.pt"
    last_weights = weights_dir / "last.pt"

    print("Training finished.")
    print(f"Run directory: {project_path / args.name}")
    print(f"Best weights: {best_weights}")
    print(f"Last weights: {last_weights}")
    print("Copy best.pt to backend/storage/models/best.pt when ready for API inference.")


if __name__ == "__main__":
    main()
