"""폴리곤(마스크) 내보내기 로직 테스트 — SAM/torch 불필요(라벨에 폴리곤을 수동 주입).

실행: python prototypes/image-understanding/test_segmentation.py
"""

import json

from labeling import (
    LabelRecord,
    record_has_masks,
    to_coco,
    to_yolo_seg,
)


def _rec_with_poly() -> LabelRecord:
    return LabelRecord(
        image_filename="road.png",
        image_width=100,
        image_height=200,
        labels=[
            {
                "class_name": "포트홀",
                "box_2d": [100, 200, 300, 400],
                # 0~1000 정규화 삼각형 폴리곤.
                "polygon": [[200, 100], [400, 100], [300, 300]],
            }
        ],
    )


def _rec_no_poly() -> LabelRecord:
    return LabelRecord(
        image_filename="road.png",
        image_width=100,
        image_height=200,
        labels=[{"class_name": "포트홀", "box_2d": [100, 200, 300, 400]}],
    )


def test_record_has_masks():
    assert record_has_masks(_rec_with_poly()) is True
    assert record_has_masks(_rec_no_poly()) is False


def test_yolo_seg_uses_polygon():
    line = to_yolo_seg(_rec_with_poly()).splitlines()[0]
    parts = line.split()
    assert parts[0] == "0"  # class id
    # 폴리곤 3점 → 6개 좌표값 (+ class id = 7 토큰)
    assert len(parts) == 1 + 6
    # 첫 점 (200,100)/1000 = (0.2, 0.1)
    assert abs(float(parts[1]) - 0.2) < 1e-6
    assert abs(float(parts[2]) - 0.1) < 1e-6


def test_yolo_seg_falls_back_to_box():
    # 폴리곤 없으면 박스 4꼭짓점(=8좌표) 으로 대체.
    line = to_yolo_seg(_rec_no_poly()).splitlines()[0]
    parts = line.split()
    assert len(parts) == 1 + 8


def test_coco_includes_segmentation():
    coco = to_coco(_rec_with_poly())
    ann = coco["annotations"][0]
    assert "segmentation" in ann
    seg = ann["segmentation"][0]
    # 첫 점 절대픽셀: x=0.2*100=20, y=0.1*200=20
    assert seg[0] == 20.0
    assert seg[1] == 20.0


def test_coco_no_segmentation_without_polygon():
    ann = to_coco(_rec_no_poly())["annotations"][0]
    assert "segmentation" not in ann


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} tests passed.")
    print(json.dumps(to_coco(_rec_with_poly())["annotations"][0], ensure_ascii=True))
