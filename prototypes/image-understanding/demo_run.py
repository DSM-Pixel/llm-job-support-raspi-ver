"""필수 1+2 엔드투엔드 시연 (Gemini 키 불필요, 수동 라벨링 경로).

흐름: 샘플 이미지 → 수동 박스 입력 → 다시 그리기 → YOLO/COCO 내보내기 → mock 저장.
실행: python prototypes/image-understanding/demo_run.py
"""

import os

from PIL import Image

import app
import backend_client

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    img_path = os.path.join(HERE, "_samples", "bengaluru.jpg")
    image = Image.open(img_path)
    image.filename = "bengaluru.jpg"
    print(f"이미지: {image.size[0]}x{image.size[1]}  ({img_path})")

    # 사용자가 표에 직접 입력했다고 가정한 박스(0~1000 정규화).
    table = [
        ["차량", 600, 100, 760, 320],
        ["차량", 580, 360, 720, 560],
        ["사람", 500, 700, 720, 800],
        ["", 0, 0, 0, 0],            # 빈 행(무시되어야 함)
    ]
    print("\n[1] 수동 보정(apply_edits) 실행...")
    annotated, summary, record, new_table = app.apply_edits(table, image)
    print("  ", summary.replace("\n", "\n   "))
    print("   정리된 표:", new_table)

    out_annotated = os.path.join(HERE, "_samples", "_demo_annotated.png")
    annotated.save(out_annotated)
    print(f"   결과 이미지 저장 → {out_annotated}")

    print("\n[2] 내보내기 (YOLO)...")
    yolo_files = app.export_labels(record, "YOLO")
    for f in yolo_files:
        print("   ", f)
    print("    내용:")
    with open(yolo_files[0], encoding="utf-8") as fh:
        for line in fh.read().splitlines():
            print("     ", line)

    print("\n[3] 내보내기 (COCO)...")
    coco_files = app.export_labels(record, "COCO")
    print("   ", coco_files[0])

    print("\n[4] mock 백엔드 저장...")
    resp = backend_client.save_labeling(record, annotated)
    print("    status:", resp["status"], "| backend:", resp["backend"])
    print("    record_id:", resp["record_id"])
    print("    saved_path:", resp["saved_path"])
    print("    저장 파일:", os.listdir(resp["saved_path"]))

    print("\n✅ 전체 흐름 정상 동작.")
    return out_annotated


if __name__ == "__main__":
    main()
