# YOLO Fine-Tuning Workflow

This folder contains command-line scripts for preparing datasets, fine-tuning YOLO with Ultralytics, evaluating a model, predicting on images, and comparing base versus fine-tuned model outputs.

The scripts do not create fake training data. They validate inputs and fail with clear messages when datasets, model files, or dependencies are missing.

## Dataset Format

Use standard YOLO format:

```text
dataset/
  images/
    train/
    val/
  labels/
    train/
    val/
  data.yaml
```

Each label file should match an image filename and contain YOLO annotations:

```text
class_id x_center y_center width height
```

Coordinates are normalized from 0 to 1.

See `data.yaml.example` for pothole and road-damage classes.

## Validate Dataset

```bash
cd backend
python app/ml/finetuning/prepare_dataset.py --dataset-dir /path/to/dataset
```

Optionally check for a specific dataset config:

```bash
python app/ml/finetuning/prepare_dataset.py \
  --dataset-dir /path/to/dataset \
  --data-yaml /path/to/dataset/data.yaml
```

## Train

```bash
cd backend
python app/ml/finetuning/train_yolo.py \
  --data /path/to/dataset/data.yaml \
  --model yolo11n.pt \
  --epochs 50 \
  --imgsz 640 \
  --batch 16 \
  --project storage/results \
  --name road_damage_yolo
```

After training, copy the best weights into the backend model directory:

```bash
cp storage/results/road_damage_yolo/weights/best.pt storage/models/best.pt
```

Do not commit `.pt` files.

## Predict

```bash
cd backend
python app/ml/finetuning/predict_yolo.py \
  --model storage/models/best.pt \
  --image /path/to/sample.jpg
```

The script prints JSON containing labels, confidence scores, and bounding boxes.

## Evaluate

```bash
cd backend
python app/ml/finetuning/evaluate_yolo.py \
  --model storage/models/best.pt \
  --data /path/to/dataset/data.yaml \
  --imgsz 640 \
  --batch 16
```

If Ultralytics exposes metrics, they are printed as JSON.

## Compare Base vs Fine-Tuned

```bash
cd backend
python app/ml/finetuning/compare_results.py \
  --base-model yolo11n.pt \
  --fine-tuned-model storage/models/best.pt \
  --image /path/to/sample.jpg
```

The comparison JSON is printed and saved under `storage/results/` by default.

## Common Errors

- `ultralytics is not installed`: run `python -m pip install -r requirements.txt`.
- `Dataset folder missing`: create the required YOLO folders before training.
- `data.yaml not found`: pass the correct `--data` or `--data-yaml` path.
- `Model file not found`: pass a valid local `.pt` file or allow Ultralytics to resolve/download the named model during CLI training.
- `No GPU available`: reduce `--batch`, use CPU training, or run on a GPU machine. The backend API itself does not require GPU because it has mock fallback behavior.

