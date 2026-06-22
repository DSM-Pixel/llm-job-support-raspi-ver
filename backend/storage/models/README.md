# 모델 가중치 (best.pt)

라벨링 "AI 자동 탐지"는 이 폴더의 `best.pt`(YOLO 도로파손 모델, 클래스: pothole/crack/road_damage)를
사용합니다. 가중치 파일은 용량이 커서 git에 커밋하지 않습니다(`.gitignore`의 `*.pt`).

## best.pt 두는 법

이 경로에 `best.pt`를 두면 실제 탐지가 켜집니다:

```
backend/storage/models/best.pt
```

- 출처: `geunyoung0120/abc_project_geunyoung` 의 `backend/storage/models/best.pt`
- 또는 `backend/ml/finetuning/train_yolo.py` 로 직접 학습해 생성

## 없을 때

파일이 없거나 ultralytics/torch 미설치 시, `yolo_service` 가 자동으로 MOCK 박스로
폴백하므로 UI는 그대로 동작합니다(탐지 결과만 가짜).

실제 탐지 의존성 설치:

```bash
uv pip install -e ".[vision]"   # ultralytics, opencv-python, torch
```
