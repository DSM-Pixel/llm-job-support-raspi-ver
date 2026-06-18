"""라벨 불러오기(from_*) 라운드트립 테스트 — API/torch 불필요.

실행: python prototypes/image-understanding/test_load.py
"""

from labeling import (
    LabelRecord,
    from_coco,
    from_record_dict,
    from_yolo,
    to_coco,
    to_yolo,
    to_yolo_seg,
)


def _rec() -> LabelRecord:
    return LabelRecord(
        image_filename="road.png",
        image_width=100,
        image_height=200,
        labels=[
            {"class_name": "포트홀", "box_2d": [100, 200, 300, 400], "confidence": 80},
            {"class_name": "균열", "box_2d": [500, 100, 800, 600],
             "polygon": [[100, 500], [600, 520], [350, 800]]},
        ],
    )


def test_meta_roundtrip_exact():
    # 우리 포맷은 완전 복원되어야(신뢰도·폴리곤 포함).
    rec = _rec()
    back = from_record_dict(rec.to_dict())
    assert back.labels == rec.labels
    assert back.image_width == 100 and back.image_height == 200


def test_coco_roundtrip_boxes():
    rec = _rec()
    back = from_coco(to_coco(rec))
    assert len(back.labels) == 2
    names = [lb["class_name"] for lb in back.labels]
    assert names == ["포트홀", "균열"]
    # 박스 좌표는 픽셀 왕복으로 ±2 오차 허용.
    for orig, got in zip(rec.labels, back.labels):
        for a, b in zip(orig["box_2d"], got["box_2d"]):
            assert abs(a - b) <= 2
    # 두 번째는 폴리곤(segmentation) 복원.
    assert "polygon" in back.labels[1]
    assert len(back.labels[1]["polygon"]) == 3


def test_yolo_roundtrip_with_classnames():
    rec = _rec()
    text = to_yolo(rec)  # class id 는 정렬된 클래스맵 기준(균열=0, 포트홀=1)
    names = sorted({lb["class_name"] for lb in rec.labels})  # ['균열','포트홀']
    back = from_yolo(text, names)  # list[dict] 반환
    assert {lb["class_name"] for lb in back} == {"포트홀", "균열"}


def test_yolo_seg_roundtrip_polygon():
    rec = _rec()
    text = to_yolo_seg(rec)
    names = sorted({lb["class_name"] for lb in rec.labels})
    back = from_yolo(text, names)  # list[dict] 반환
    # 균열은 폴리곤이 있으므로 세그 라인 → polygon 복원.
    crack = next(lb for lb in back if lb["class_name"] == "균열")
    assert "polygon" in crack and len(crack["polygon"]) == 3


def test_yolo_unknown_class_fallback():
    back = from_yolo("3 0.5 0.5 0.2 0.2", [])  # 클래스명 없음 → class_3
    assert back[0]["class_name"] == "class_3"


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} tests passed.")
