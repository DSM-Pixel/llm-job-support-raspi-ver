"""실제 Gemini 자동 탐지 시연 (키 필요).

흐름: 샘플 이미지 → Gemini 자동 탐지 → 박스 그리기 → mock 저장.
실행: python prototypes/image-understanding/demo_real.py [대상]
"""

import os
import sys

from PIL import Image

import app
import backend_client

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "차량"
    print("client 준비됨:", app.client is not None, "| 모델:", app.MODEL)

    img_path = os.path.join(HERE, "_samples", "bengaluru.jpg")
    image = Image.open(img_path)
    image.filename = "bengaluru.jpg"
    print(f"이미지: {image.size[0]}x{image.size[1]} | 대상='{target}'")

    print("\n[Gemini 자동 탐지 중...]")
    annotated, summary, record, table = app.detect(image, target)
    print(summary.replace("\n", "\n  "))

    out = os.path.join(HERE, "_samples", "_demo_real.png")
    annotated.save(out)
    print(f"\n결과 이미지 → {out}")

    if record.labels:
        resp = backend_client.save_labeling(record, annotated)
        print("mock 저장:", resp["status"], "->", resp["saved_path"])
    return out


if __name__ == "__main__":
    main()
