"""라벨 데이터 모델 + 내보내기(YOLO / COCO) 순수 함수 모음.

Gradio·API에 의존하지 않으므로 단독 테스트가 쉽다.
박스 좌표 규약은 앱 전체에서 Gemini 규약을 그대로 따른다:
    box_2d = [ymin, xmin, ymax, xmax], 0~1000 정규화 정수.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

# 0~1000 정규화 좌표의 최댓값(Gemini 규약).
NORM = 1000.0


@dataclass
class LabelRecord:
    """한 장의 이미지에 대한 라벨링 결과(저장/내보내기의 단일 원천)."""

    image_filename: str
    image_width: int
    image_height: int
    # 각 라벨: {"class_name": str, "box_2d": [ymin, xmin, ymax, xmax]}
    labels: list[dict] = field(default_factory=list)

    def class_names(self) -> list[str]:
        """등장한 클래스 이름을 정렬해 반환(클래스 id 매핑의 기준)."""
        return sorted({lb["class_name"] for lb in self.labels})

    def to_dict(self) -> dict:
        return {
            "image_filename": self.image_filename,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "labels": self.labels,
        }


def build_class_map(record: LabelRecord) -> dict[str, int]:
    """클래스 이름 → 0부터 시작하는 정수 id 매핑."""
    return {name: i for i, name in enumerate(record.class_names())}


def _box_to_corners_norm(box_2d: list[int]) -> tuple[float, float, float, float]:
    """[ymin,xmin,ymax,xmax](0~1000) → (x1,y1,x2,y2) 0~1 정규화 코너."""
    ymin, xmin, ymax, xmax = box_2d
    x1, x2 = xmin / NORM, xmax / NORM
    y1, y2 = ymin / NORM, ymax / NORM
    # 좌표 뒤집힘 방지(모델이 가끔 min/max를 바꿔서 줌).
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return x1, y1, x2, y2


def to_yolo(record: LabelRecord, class_map: dict[str, int] | None = None) -> str:
    """YOLO txt 형식 문자열 생성.

    각 줄: `class_id x_center y_center width height` (모두 0~1 정규화).
    """
    cmap = class_map or build_class_map(record)
    lines: list[str] = []
    for lb in record.labels:
        box = lb.get("box_2d")
        if not box or len(box) != 4:
            continue
        x1, y1, x2, y2 = _box_to_corners_norm(box)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        w, h = x2 - x1, y2 - y1
        if w <= 0 or h <= 0:
            continue
        cid = cmap[lb["class_name"]]
        lines.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return "\n".join(lines)


def _polygon_to_abs(polygon, w_img: int, h_img: int) -> list[float]:
    """0~1000 정규화 폴리곤 점들 → COCO segmentation용 절대 픽셀 [x1,y1,x2,y2,...]."""
    flat: list[float] = []
    for x, y in polygon:
        flat.append(round(x / NORM * w_img, 2))
        flat.append(round(y / NORM * h_img, 2))
    return flat


def to_coco(record: LabelRecord, class_map: dict[str, int] | None = None) -> dict:
    """COCO JSON(단일 이미지) 생성. bbox는 절대 픽셀 [x,y,w,h], polygon 있으면 segmentation 포함."""
    cmap = class_map or build_class_map(record)
    w_img, h_img = record.image_width, record.image_height

    categories = [{"id": cid, "name": name} for name, cid in sorted(cmap.items(), key=lambda kv: kv[1])]
    images = [{"id": 1, "file_name": record.image_filename, "width": w_img, "height": h_img}]

    annotations: list[dict] = []
    ann_id = 1
    for lb in record.labels:
        box = lb.get("box_2d")
        if not box or len(box) != 4:
            continue
        x1, y1, x2, y2 = _box_to_corners_norm(box)
        px, py = x1 * w_img, y1 * h_img
        bw, bh = (x2 - x1) * w_img, (y2 - y1) * h_img
        if bw <= 0 or bh <= 0:
            continue
        ann = {
            "id": ann_id,
            "image_id": 1,
            "category_id": cmap[lb["class_name"]],
            "bbox": [round(px, 2), round(py, 2), round(bw, 2), round(bh, 2)],
            "area": round(bw * bh, 2),
            "iscrowd": 0,
        }
        poly = lb.get("polygon")
        if poly and len(poly) >= 3:
            ann["segmentation"] = [_polygon_to_abs(poly, w_img, h_img)]
        annotations.append(ann)
        ann_id += 1

    return {"images": images, "annotations": annotations, "categories": categories}


def to_yolo_seg(record: LabelRecord, class_map: dict[str, int] | None = None) -> str:
    """YOLO segmentation 형식. 각 줄: `class_id x1 y1 x2 y2 ... xn yn` (0~1 정규화).

    polygon 이 있으면 그걸 쓰고, 없으면 박스 네 꼭짓점을 폴리곤으로 대체한다.
    """
    cmap = class_map or build_class_map(record)
    lines: list[str] = []
    for lb in record.labels:
        box = lb.get("box_2d")
        if not box or len(box) != 4:
            continue
        cid = cmap[lb["class_name"]]
        poly = lb.get("polygon")
        if poly and len(poly) >= 3:
            pts = [(x / NORM, y / NORM) for x, y in poly]
        else:
            x1, y1, x2, y2 = _box_to_corners_norm(box)
            pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        coords = " ".join(f"{x:.6f} {y:.6f}" for x, y in pts)
        lines.append(f"{cid} {coords}")
    return "\n".join(lines)


def record_has_masks(record: LabelRecord) -> bool:
    """폴리곤(마스크)이 하나라도 있는지."""
    return any(lb.get("polygon") for lb in record.labels)


def yolo_classes_txt(record: LabelRecord, class_map: dict[str, int] | None = None) -> str:
    """YOLO classes.txt(id 순서대로 클래스 이름 한 줄씩)."""
    cmap = class_map or build_class_map(record)
    return "\n".join(name for name, _ in sorted(cmap.items(), key=lambda kv: kv[1]))


def to_coco_json(record: LabelRecord) -> str:
    """COCO dict을 보기 좋은 JSON 문자열로."""
    return json.dumps(to_coco(record), ensure_ascii=False, indent=2)


# ────────────────────────────────────────────────────────────────────
# 불러오기(이어서 작업) — 저장된 라벨을 다시 LabelRecord/labels 로 복원.
# 지원: 우리 meta.json(완전 복원) · COCO json · YOLO txt.
# 좌표는 항상 0~1000 정규화로 통일하므로 원본 해상도와 무관하게 재사용 가능.
# ────────────────────────────────────────────────────────────────────


def from_record_dict(d: dict) -> LabelRecord:
    """우리 포맷(meta.json = LabelRecord.to_dict) → LabelRecord. 완전 복원."""
    return LabelRecord(
        image_filename=d.get("image_filename") or "image.png",
        image_width=int(d.get("image_width") or 0),
        image_height=int(d.get("image_height") or 0),
        labels=list(d.get("labels") or []),
    )


def from_coco(coco: dict) -> LabelRecord:
    """COCO json(단일 이미지) → LabelRecord. bbox·segmentation·score 복원."""
    img = (coco.get("images") or [{}])[0]
    w = int(img.get("width") or 0)
    h = int(img.get("height") or 0)
    cats = {c["id"]: c["name"] for c in coco.get("categories", [])}

    labels = []
    for ann in coco.get("annotations", []):
        bbox = ann.get("bbox")
        if not bbox or len(bbox) != 4 or not w or not h:
            continue
        x, y, bw, bh = bbox
        box = [
            round(y / h * NORM),  # ymin
            round(x / w * NORM),  # xmin
            round((y + bh) / h * NORM),  # ymax
            round((x + bw) / w * NORM),  # xmax
        ]
        lb = {"class_name": cats.get(ann.get("category_id"), f"class_{ann.get('category_id')}"),
              "box_2d": box}
        seg = ann.get("segmentation")
        if isinstance(seg, list) and seg and isinstance(seg[0], list):
            flat = seg[0]
            poly = [
                [round(flat[i] / w * NORM, 1), round(flat[i + 1] / h * NORM, 1)]
                for i in range(0, len(flat) - 1, 2)
            ]
            if len(poly) >= 3:
                lb["polygon"] = poly
        sc = ann.get("score")
        if isinstance(sc, (int, float)):
            lb["confidence"] = max(0, min(100, int(round(sc * 100 if sc <= 1 else sc))))
        labels.append(lb)
    return LabelRecord(img.get("file_name") or "image.png", w, h, labels)


def from_yolo(text: str, class_names: list[str] | None = None) -> list[dict]:
    """YOLO txt(박스 또는 세그) → labels. 좌표 0~1 정규화이므로 크기 정보 불필요."""
    names = class_names or []
    labels = []
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            cid = int(float(parts[0]))
            nums = [float(v) for v in parts[1:]]
        except ValueError:
            continue
        name = names[cid] if 0 <= cid < len(names) else f"class_{cid}"
        if len(nums) == 4:
            cx, cy, bw, bh = nums
            box = [
                round((cy - bh / 2) * NORM), round((cx - bw / 2) * NORM),
                round((cy + bh / 2) * NORM), round((cx + bw / 2) * NORM),
            ]
            labels.append({"class_name": name, "box_2d": box})
        elif len(nums) >= 6 and len(nums) % 2 == 0:
            poly = [[round(nums[i] * NORM, 1), round(nums[i + 1] * NORM, 1)]
                    for i in range(0, len(nums), 2)]
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            box = [round(min(ys)), round(min(xs)), round(max(ys)), round(max(xs))]
            labels.append({"class_name": name, "box_2d": box, "polygon": poly})
    return labels
