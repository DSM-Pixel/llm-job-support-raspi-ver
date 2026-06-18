"""백엔드 저장 클라이언트 (현재 MOCK).

라벨링 결과(이미지 + 라벨 + 내보내기 파일)를 백엔드에 저장하는 경계(boundary).
지금은 로컬 `_saved/` 폴더에 저장하고 가짜 응답을 돌려준다.

────────────────────────────────────────────────────────────────────
백엔드 팀과 합칠 때: 아래 `save_labeling()` 함수 본문만 실제 API 호출로
교체하면 된다. 입력(record/이미지)·출력(dict) 계약은 그대로 유지할 것.

기대 응답 계약(실제 백엔드도 이 모양을 맞춰주면 UI 수정 불필요):
    {
        "status": "ok" | "error",
        "record_id": str,          # 저장된 라벨 레코드 식별자
        "saved_path": str,         # 저장 위치(또는 URL)
        "backend": "MOCK" | "...", # 어떤 백엔드가 처리했는지
        "message": str,            # 사용자 표시용 메시지
    }
────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import io
import json
import os
import re
from datetime import datetime

from PIL import Image

from labeling import LabelRecord, to_coco, to_yolo, yolo_classes_txt

# MOCK 저장 루트(이 파일 기준 _saved/).
_HERE = os.path.dirname(os.path.abspath(__file__))
_SAVE_ROOT = os.path.join(_HERE, "_saved")


def _slugify(name: str) -> str:
    """파일/폴더명에 안전한 형태로 정리."""
    base = os.path.splitext(name or "image")[0]
    base = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", base).strip("_")
    return base or "image"


def save_labeling(record: LabelRecord, annotated_image: Image.Image | None = None) -> dict:
    """라벨링 결과를 백엔드에 저장한다. (현재 MOCK: 로컬 디스크에 기록)

    Args:
        record: 라벨 레코드(단일 원천).
        annotated_image: 박스가 그려진 결과 이미지(선택).

    Returns:
        응답 계약 dict (위 모듈 docstring 참고).
    """
    if record is None or not record.labels:
        return {
            "status": "error",
            "record_id": "",
            "saved_path": "",
            "backend": "MOCK",
            "message": "저장할 라벨이 없습니다. 먼저 '박스로 찾기'를 실행하세요.",
        }

    # ── 여기부터 MOCK 구현 (실제 연동 시 이 블록을 API 호출로 교체) ──
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    record_id = f"{stamp}_{_slugify(record.image_filename)}"
    out_dir = os.path.join(_SAVE_ROOT, record_id)
    os.makedirs(out_dir, exist_ok=True)

    # 1) 메타/원천 레코드
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)

    # 2) YOLO
    with open(os.path.join(out_dir, "labels.yolo.txt"), "w", encoding="utf-8") as f:
        f.write(to_yolo(record))
    with open(os.path.join(out_dir, "classes.txt"), "w", encoding="utf-8") as f:
        f.write(yolo_classes_txt(record))

    # 3) COCO
    with open(os.path.join(out_dir, "labels.coco.json"), "w", encoding="utf-8") as f:
        json.dump(to_coco(record), f, ensure_ascii=False, indent=2)

    # 4) 결과 이미지(있으면)
    if annotated_image is not None:
        annotated_image.convert("RGB").save(os.path.join(out_dir, "annotated.png"))

    # 실제 백엔드라면 여기서 요청 바이트를 만들어 보낼 것이다(예시는 미사용).
    _ = io.BytesIO()
    # ── MOCK 구현 끝 ──

    return {
        "status": "ok",
        "record_id": record_id,
        "saved_path": out_dir,
        "backend": "MOCK",
        "message": f"[MOCK] 라벨 {len(record.labels)}건을 저장했습니다.",
    }
