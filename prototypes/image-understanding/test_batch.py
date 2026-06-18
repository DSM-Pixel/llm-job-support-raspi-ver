"""배치 처리(batch_process) 테스트 — Gemini 호출은 monkeypatch로 대체(키 불필요).

실행: python prototypes/image-understanding/test_batch.py
"""

import os
import tempfile
import zipfile

from PIL import Image

import app


def _make_images(n: int) -> list[str]:
    d = tempfile.mkdtemp(prefix="batch_in_")
    paths = []
    for i in range(n):
        p = os.path.join(d, f"img_{i}.png")
        Image.new("RGB", (100, 100), "gray").save(p)
        paths.append(p)
    return paths


def test_batch_happy_path(monkeypatch):
    # _detect_labels를 가짜로: 항상 박스 2개 반환.
    def fake_detect(image, target):
        return [
            {"class_name": target, "box_2d": [100, 100, 200, 200]},
            {"class_name": target, "box_2d": [300, 300, 500, 500]},
        ]

    monkeypatch.setattr(app, "_detect_labels", fake_detect)
    files = _make_images(3)
    rows, zip_path, summary = app.batch_process(files, "포트홀", save_backend=False, delay=0)

    assert len(rows) == 3
    assert all(r[1] == 2 and r[2] == "완료" for r in rows)
    assert "3/3장" in summary
    # zip 안에 이미지별 YOLO/COCO + classes.txt 가 있어야.
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
    assert "classes.txt" in names
    assert sum(1 for n in names if n.endswith(".txt")) == 4  # img 3개 + classes
    assert sum(1 for n in names if n.endswith(".coco.json")) == 3


def test_batch_continues_on_error(monkeypatch):
    # 두 번째 이미지에서 재시도 불가능한 오류 → 멈추지 않고 나머지 처리.
    calls = {"n": 0}

    def flaky_detect(image, target):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("이미지 디코딩 실패")  # 429 아님 → 재시도 없이 즉시 오류.
        return [{"class_name": target, "box_2d": [0, 0, 100, 100]}]

    monkeypatch.setattr(app, "_detect_labels", flaky_detect)
    files = _make_images(3)
    rows, zip_path, summary = app.batch_process(files, "차량", save_backend=False, delay=0)

    assert len(rows) == 3
    statuses = [r[2] for r in rows]
    assert statuses[0] == "완료"
    assert statuses[1].startswith("오류")
    assert "한도초과" not in statuses[1]  # 일반 오류이므로.
    assert statuses[2] == "완료"
    assert "2/3장" in summary


def test_batch_retry_recovers_from_429(monkeypatch):
    # 첫 호출은 429, 재시도에서 성공 → 최종 '완료'여야.
    calls = {"n": 0}

    def once_429(image, target):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED retry in 0s")
        return [{"class_name": target, "box_2d": [0, 0, 100, 100]}]

    monkeypatch.setattr(app, "_detect_labels", once_429)
    monkeypatch.setattr(app.time, "sleep", lambda *_: None)  # 실제 대기 제거.
    rows, _, summary = app.batch_process(_make_images(1), "포트홀", save_backend=False, delay=0)
    assert rows[0][2] == "완료"
    assert calls["n"] == 2  # 재시도가 실제로 일어남.


def test_batch_with_mask(monkeypatch):
    # 마스크 적용: segmenter가 폴리곤을 붙여준다고 가정.
    monkeypatch.setattr(
        app, "_detect_labels", lambda i, t: [{"class_name": t, "box_2d": [0, 0, 100, 100]}]
    )

    def fake_seg(image, labels):
        out = [dict(lb, polygon=[[0, 0], [100, 0], [100, 100]]) for lb in labels]
        return out, "정밀 마스크 1/1개 생성."

    monkeypatch.setattr(app.segmenter, "segment_labels", fake_seg)
    rows, _, summary = app.batch_process(
        _make_images(2), "포트홀", save_backend=False, use_mask=True, delay=0
    )
    assert all("마스크 1" in r[2] for r in rows)
    assert "정밀 마스크 2개" in summary


def test_batch_delay_called(monkeypatch):
    # 3장 처리 시 호출 간 딜레이가 (n-1)=2회 호출돼야.
    monkeypatch.setattr(app, "_detect_labels", lambda i, t: [])
    sleeps = []
    monkeypatch.setattr(app.time, "sleep", lambda s: sleeps.append(s))
    app.batch_process(_make_images(3), "포트홀", save_backend=False, delay=3)
    assert sleeps == [3, 3]


def test_batch_empty_raises():
    try:
        app.batch_process([], "포트홀", False)
    except Exception as e:  # gr.Error
        assert "이미지" in str(e)
    else:
        raise AssertionError("빈 입력인데 예외가 없음")


# --- 초간단 monkeypatch 셰임(테스트 러너 없이 단독 실행용) ---
class _MP:
    def __init__(self):
        self._undo = []

    def setattr(self, obj, name, val):
        self._undo.append((obj, name, getattr(obj, name)))
        setattr(obj, name, val)

    def undo(self):
        for obj, name, val in reversed(self._undo):
            setattr(obj, name, val)


if __name__ == "__main__":
    passed = 0
    mp_tests = [
        "test_batch_happy_path",
        "test_batch_continues_on_error",
        "test_batch_retry_recovers_from_429",
        "test_batch_with_mask",
        "test_batch_delay_called",
    ]
    for tname in mp_tests:
        mp = _MP()
        try:
            globals()[tname](mp)
        finally:
            mp.undo()
        print(f"  PASS {tname}")
        passed += 1
    test_batch_empty_raises()
    print("  PASS test_batch_empty_raises")
    passed += 1
    print(f"\n{passed} tests passed.")
