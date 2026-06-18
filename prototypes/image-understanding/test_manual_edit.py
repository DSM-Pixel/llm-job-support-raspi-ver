"""수동 보정(apply_edits) 스모크 테스트 — API 키 불필요.

실행: python prototypes/image-understanding/test_manual_edit.py
app.py를 임포트하지만 GEMINI 키가 없으면 client=None 이라 네트워크 호출은 없다.
"""

from PIL import Image

import app


def _img():
    return Image.new("RGB", (100, 200), "gray")


def test_labels_to_rows_roundtrip():
    # 6열: 클래스, ymin, xmin, ymax, xmax, conf(없으면 "").
    labels = [{"class_name": "포트홀", "box_2d": [10, 20, 30, 40]}]
    assert app.labels_to_rows(labels) == [["포트홀", 10, 20, 30, 40, ""]]
    labels2 = [{"class_name": "균열", "box_2d": [1, 2, 3, 4], "confidence": 88}]
    assert app.labels_to_rows(labels2) == [["균열", 1, 2, 3, 4, 88]]


def test_apply_edits_cleans_and_draws():
    # 유효 1행 + 빈클래스 1행 + 숫자아님 1행 + 면적0 1행 → 유효 1개만 남아야.
    table = [
        ["포트홀", 100, 200, 300, 400, ""],
        ["", 0, 0, 100, 100, ""],            # 클래스 비어있음 → 제거
        ["균열", "x", 0, 100, 100, ""],       # 좌표 숫자아님 → 제거
        ["맨홀", 50, 50, 50, 50, ""],         # 면적 0 → 제거
    ]
    annotated, summary, record, new_table = app.apply_edits(table, _img())
    assert len(record.labels) == 1
    assert record.labels[0]["class_name"] == "포트홀"
    assert record.labels[0]["box_2d"] == [100, 200, 300, 400]
    assert new_table == [["포트홀", 100, 200, 300, 400, ""]]
    assert "총 1개" in summary
    assert annotated.size == (100, 200)


def test_apply_edits_preserves_confidence():
    table = [["포트홀", 100, 200, 300, 400, 73]]
    _, _, record, new_table = app.apply_edits(table, _img())
    assert record.labels[0]["confidence"] == 73
    assert new_table == [["포트홀", 100, 200, 300, 400, 73]]


def test_parse_targets():
    assert app.parse_targets("포트홀") == ["포트홀"]
    assert app.parse_targets("포트홀, 균열 , 포트홀") == ["포트홀", "균열"]  # 중복 제거, 순서 유지
    assert app.parse_targets("  ,  ") == []


def test_filter_by_confidence():
    labels = [
        {"class_name": "a", "box_2d": [0, 0, 1, 1], "confidence": 90},
        {"class_name": "b", "box_2d": [0, 0, 1, 1], "confidence": 40},
        {"class_name": "c", "box_2d": [0, 0, 1, 1]},  # conf 없음 → 통과(보수적)
    ]
    kept = app.filter_by_confidence(labels, 50)
    names = {lb["class_name"] for lb in kept}
    assert names == {"a", "c"}
    # 0이면 필터 끔(전부 통과).
    assert len(app.filter_by_confidence(labels, 0)) == 3


def test_apply_edits_clamps_out_of_range():
    table = [["차량", -50, 0, 2000, 500]]  # ymin<0, ymax>1000 → 0,1000 클램프
    _, _, record, _ = app.apply_edits(table, _img())
    assert record.labels[0]["box_2d"] == [0, 0, 1000, 500]


def test_apply_edits_manual_only_multi_class():
    # 탐지 없이 직접 입력한 다중 클래스.
    table = [["포트홀", 0, 0, 200, 200], ["균열", 300, 300, 600, 600]]
    _, summary, record, _ = app.apply_edits(table, _img())
    assert {lb["class_name"] for lb in record.labels} == {"포트홀", "균열"}
    assert "총 2개" in summary


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} tests passed.")
