"""라벨링 결과 집계(통계 대시보드용) 순수 함수.

저장된 meta.json(=LabelRecord)들을 읽어 클래스 분포·신뢰도 분포·이미지별
박스 수 등을 계산한다. Gradio/차트에 의존하지 않아 단독 테스트가 쉽다.
"""

from __future__ import annotations

import glob
import json
import os

from labeling import LabelRecord, from_record_dict

# 신뢰도 히스토그램 구간(0~100).
CONF_BINS = ["0-19", "20-39", "40-59", "60-79", "80-100"]


def load_saved_records(saved_dir: str) -> list[LabelRecord]:
    """`_saved/<id>/meta.json` 들을 모두 읽어 LabelRecord 목록으로."""
    records = []
    for meta in sorted(glob.glob(os.path.join(saved_dir, "*", "meta.json"))):
        try:
            with open(meta, encoding="utf-8") as f:
                records.append(from_record_dict(json.load(f)))
        except (OSError, json.JSONDecodeError):
            continue  # 깨진 파일은 건너뜀.
    return records


def _conf_bin(c: float) -> str:
    if c < 20:
        return CONF_BINS[0]
    if c < 40:
        return CONF_BINS[1]
    if c < 60:
        return CONF_BINS[2]
    if c < 80:
        return CONF_BINS[3]
    return CONF_BINS[4]


def aggregate(records: list[LabelRecord]) -> dict:
    """레코드 목록 → 집계 통계 dict."""
    class_counts: dict[str, int] = {}
    conf_hist = {b: 0 for b in CONF_BINS}
    boxes_per_image = []
    n_labels = 0
    n_conf = 0
    mask_labels = 0

    for r in records:
        boxes_per_image.append({"image": r.image_filename, "boxes": len(r.labels)})
        for lb in r.labels:
            n_labels += 1
            name = lb.get("class_name", "?")
            class_counts[name] = class_counts.get(name, 0) + 1
            if lb.get("polygon"):
                mask_labels += 1
            c = lb.get("confidence")
            if isinstance(c, (int, float)):
                conf_hist[_conf_bin(c)] += 1
                n_conf += 1

    avg_boxes = round(n_labels / len(records), 2) if records else 0
    return {
        "n_images": len(records),
        "n_labels": n_labels,
        "n_classes": len(class_counts),
        "class_counts": class_counts,
        "conf_hist": conf_hist,
        "n_conf": n_conf,
        "mask_labels": mask_labels,
        "avg_boxes": avg_boxes,
        "boxes_per_image": boxes_per_image,
    }
