"""SAM 정밀 마스크 시연 — Gemini 호출 없이 알려진 박스 재사용(쿼터 절약).

실행: python prototypes/image-understanding/demo_mask.py
"""

import os
import time

from PIL import Image

import app
import segmenter
from labeling import LabelRecord, to_yolo_seg

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    print("SAM 사용 가능:", segmenter.is_available())
    image = Image.open(os.path.join(HERE, "_samples", "bengaluru.jpg"))
    image.filename = "bengaluru.jpg"

    # 앞 단계에서 Gemini가 찾은 포트홀 박스 재사용.
    labels = [{"class_name": "포트홀", "box_2d": [360, 264, 525, 770]}]

    print("SAM 마스크 생성 중(첫 실행은 모델 다운로드로 느릴 수 있음)...")
    t0 = time.time()
    new_labels, msg = segmenter.segment_labels(image, labels)
    print(f"  {msg}  ({time.time() - t0:.1f}s)")

    poly = new_labels[0].get("polygon")
    print("  폴리곤 점 개수:", len(poly) if poly else 0)

    annotated, summary = app._draw_boxes(image, new_labels)
    out = os.path.join(HERE, "_samples", "_demo_mask.png")
    annotated.save(out)
    print("  결과 이미지 →", out)
    print(summary.replace("\n", "\n  "))

    rec = LabelRecord("bengaluru.jpg", *image.convert("RGB").size, new_labels)
    print("\nYOLO-seg 첫 줄(앞 80자):")
    print("  ", to_yolo_seg(rec).splitlines()[0][:80], "...")
    return out


if __name__ == "__main__":
    main()
