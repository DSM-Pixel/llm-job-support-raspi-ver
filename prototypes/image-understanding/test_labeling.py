"""labeling / backend_client 검증 (API 키 불필요).

실행: python prototypes/image-understanding/test_labeling.py
또는: pytest prototypes/image-understanding/test_labeling.py
"""

import json

from labeling import (
    LabelRecord,
    build_class_map,
    to_coco,
    to_yolo,
    yolo_classes_txt,
)


def _sample() -> LabelRecord:
    # 100x200 이미지, 포트홀 1개 + 균열 1개.
    return LabelRecord(
        image_filename="road.png",
        image_width=100,
        image_height=200,
        labels=[
            {"class_name": "포트홀", "box_2d": [100, 200, 300, 400]},  # ymin,xmin,ymax,xmax
            {"class_name": "균열", "box_2d": [500, 0, 1000, 1000]},
        ],
    )


def test_class_map_sorted():
    cmap = build_class_map(_sample())
    assert cmap == {"균열": 0, "포트홀": 1}  # 가나다 정렬


def test_yolo_format():
    rec = _sample()
    yolo = to_yolo(rec).splitlines()
    assert len(yolo) == 2
    # 출력은 labels 순서 유지 -> yolo[0]이 포트홀.
    # 포트홀: x1=0.2,x2=0.4 -> cx=0.3,w=0.2 / y1=0.1,y2=0.3 -> cy=0.2,h=0.2, class id 1
    cid, cx, cy, w, h = yolo[0].split()
    assert cid == "1"
    assert abs(float(cx) - 0.3) < 1e-6
    assert abs(float(cy) - 0.2) < 1e-6
    assert abs(float(w) - 0.2) < 1e-6
    assert abs(float(h) - 0.2) < 1e-6


def test_coco_pixels():
    rec = _sample()
    coco = to_coco(rec)
    assert len(coco["annotations"]) == 2
    assert {c["name"] for c in coco["categories"]} == {"포트홀", "균열"}
    # 포트홀 박스(절대 픽셀): x=0.2*100=20, y=0.1*200=20, w=0.2*100=20, h=0.2*200=40
    pothole = next(a for a in coco["annotations"] if a["category_id"] == 1)
    assert pothole["bbox"] == [20.0, 20.0, 20.0, 40.0]
    assert pothole["area"] == 800.0


def test_classes_txt_order():
    assert yolo_classes_txt(_sample()).splitlines() == ["균열", "포트홀"]


def test_empty_record():
    empty = LabelRecord(image_filename="x.png", image_width=10, image_height=10, labels=[])
    assert to_yolo(empty) == ""
    assert to_coco(empty)["annotations"] == []


def _run_all():
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} tests passed.")

    # 통합: mock 백엔드 저장(이미지 없이).
    import backend_client

    resp = backend_client.save_labeling(_sample(), None)
    assert resp["status"] == "ok", resp
    # 콘솔 인코딩(cp1252) 충돌을 피하려 ascii로 출력. 파일은 utf-8로 저장됨.
    print("backend MOCK save ok ->", resp["record_id"])
    print(json.dumps(resp, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    _run_all()
