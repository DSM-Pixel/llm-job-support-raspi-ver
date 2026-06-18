"""통계 집계(stats.aggregate / load_saved_records) 테스트 — API/torch 불필요.

실행: python prototypes/image-understanding/test_stats.py
"""

import json
import os
import tempfile

import stats
from labeling import LabelRecord


def _records():
    return [
        LabelRecord("a.png", 100, 100, [
            {"class_name": "포트홀", "box_2d": [0, 0, 100, 100], "confidence": 90},
            {"class_name": "균열", "box_2d": [0, 0, 50, 50], "confidence": 30,
             "polygon": [[0, 0], [10, 0], [5, 10]]},
        ]),
        LabelRecord("b.png", 100, 100, [
            {"class_name": "포트홀", "box_2d": [0, 0, 100, 100]},  # 신뢰도 없음
        ]),
        LabelRecord("c.png", 100, 100, []),  # 객체 없음
    ]


def test_aggregate_counts():
    agg = stats.aggregate(_records())
    assert agg["n_images"] == 3
    assert agg["n_labels"] == 3
    assert agg["n_classes"] == 2
    assert agg["class_counts"] == {"포트홀": 2, "균열": 1}
    assert agg["mask_labels"] == 1
    assert agg["avg_boxes"] == 1.0  # 3라벨 / 3이미지


def test_aggregate_confidence_hist():
    agg = stats.aggregate(_records())
    # 90 → 80-100, 30 → 20-39. 신뢰도 없는 1개는 제외.
    assert agg["n_conf"] == 2
    assert agg["conf_hist"]["80-100"] == 1
    assert agg["conf_hist"]["20-39"] == 1
    assert agg["conf_hist"]["40-59"] == 0


def test_aggregate_empty():
    agg = stats.aggregate([])
    assert agg["n_images"] == 0
    assert agg["n_labels"] == 0
    assert agg["avg_boxes"] == 0


def test_load_saved_records(tmp_path=None):
    # 임시 _saved 구조를 만들어 로더 검증.
    root = tempfile.mkdtemp(prefix="saved_")
    rec_dir = os.path.join(root, "20260618_x_a")
    os.makedirs(rec_dir)
    with open(os.path.join(rec_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(
            {"image_filename": "a.png", "image_width": 10, "image_height": 10,
             "labels": [{"class_name": "포트홀", "box_2d": [0, 0, 5, 5]}]},
            f, ensure_ascii=False,
        )
    # 깨진 폴더(meta 없음)는 무시되어야.
    os.makedirs(os.path.join(root, "broken"))

    recs = stats.load_saved_records(root)
    assert len(recs) == 1
    assert recs[0].labels[0]["class_name"] == "포트홀"


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} tests passed.")
