import argparse
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LABEL_SUFFIXES = {".txt"}
EXPECTED_DIRS = [
    "images/train",
    "images/val",
    "labels/train",
    "labels/val",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a YOLO-format dataset.")
    parser.add_argument("--dataset-dir", required=True, help="Dataset root directory.")
    parser.add_argument("--data-yaml", help="Optional path to YOLO data.yaml.")
    return parser.parse_args()


def count_files(path: Path, suffixes: set[str]) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file() and item.suffix.lower() in suffixes)


def main() -> None:
    args = parse_args()
    dataset_dir = Path(args.dataset_dir).expanduser()
    if not dataset_dir.is_dir():
        raise SystemExit(f"Dataset directory not found: {dataset_dir}")

    missing_dirs = [folder for folder in EXPECTED_DIRS if not (dataset_dir / folder).is_dir()]
    if missing_dirs:
        formatted = "\n".join(f"- {folder}" for folder in missing_dirs)
        raise SystemExit(f"Missing required YOLO dataset folders:\n{formatted}")

    data_yaml = Path(args.data_yaml).expanduser() if args.data_yaml else dataset_dir / "data.yaml"
    if not data_yaml.is_file():
        raise SystemExit(
            f"YOLO data config not found: {data_yaml}\n"
            "Create it or pass --data-yaml with the correct path."
        )

    train_images = count_files(dataset_dir / "images/train", IMAGE_SUFFIXES)
    val_images = count_files(dataset_dir / "images/val", IMAGE_SUFFIXES)
    train_labels = count_files(dataset_dir / "labels/train", LABEL_SUFFIXES)
    val_labels = count_files(dataset_dir / "labels/val", LABEL_SUFFIXES)

    errors = []
    if train_images == 0:
        errors.append("No training images found in images/train.")
    if val_images == 0:
        errors.append("No validation images found in images/val.")
    if train_labels == 0:
        errors.append("No training label files found in labels/train.")
    if val_labels == 0:
        errors.append("No validation label files found in labels/val.")

    if errors:
        raise SystemExit("\n".join(errors))

    print("YOLO dataset validation passed.")
    print(f"Dataset: {dataset_dir}")
    print(f"Data config: {data_yaml}")
    print(f"Training images: {train_images}")
    print(f"Validation images: {val_images}")
    print(f"Training labels: {train_labels}")
    print(f"Validation labels: {val_labels}")


if __name__ == "__main__":
    main()
