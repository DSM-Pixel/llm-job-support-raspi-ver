"""이미지 이해·라벨링 데모 (Gemini 멀티모달, 무료 티어).

두 가지 모드:
  1) 설명 분석 — 이미지를 올리고 시나리오를 고르면 한국어 설명/라벨을 글로 받는다.
  2) 박스로 찾기 — 찾을 대상을 입력하면 Gemini가 바운딩 박스 좌표를 뽑고,
     그 위치에 박스 + 라벨을 직접 그려 보여준다(라벨링 미리보기).

Gemini 2.5 Flash 는 이미지를 직접 이해하는 멀티모달 모델이라, 별도 비전 모델
설치 없이 '이미지 + 한국어 질문' → 설명/좌표를 무료로 받아볼 수 있다.
여기서부터 실제 YOLO/SAM 같은 정밀 모델을 점진적으로 붙여나가면 된다.

실행:
    python prototypes/image-understanding/app.py
실행 후 출력되는 http://127.0.0.1:7860 주소를 브라우저에서 연다.
"""

import json
import os
import re
import shutil
import tempfile
import time

import gradio as gr
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

import backend_client
import segmenter
import stats
from labeling import (
    LabelRecord,
    from_coco,
    from_record_dict,
    from_yolo,
    record_has_masks,
    to_coco,
    to_coco_json,
    to_yolo,
    to_yolo_seg,
    yolo_classes_txt,
)

DEFAULT_MODEL = "gemini-2.5-flash"

# api-test 폴더의 .env 를 재사용(키를 한 곳에서 관리).
here = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(here, "..", "api-test", ".env"))
load_dotenv(os.path.join(here, ".env"))
load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=_api_key) if _api_key else None

# 박스 색상 팔레트(라벨별로 돌려가며 사용).
_COLORS = [
    "#FF3B30", "#34C759", "#007AFF", "#FF9500", "#AF52DE",
    "#FF2D55", "#5AC8FA", "#FFCC00", "#4CD964", "#5856D6",
]

# 자주 쓰는 분석 시나리오 프리셋. 직접 프롬프트를 쓰면 이 값은 무시된다.
PRESETS = {
    "도로 파손/포트홀 찾기": (
        "이 이미지는 도로 사진이야. 포트홀·균열 등 도로 파손이 보이면 "
        "각각 위치(예: 좌측 하단), 종류, 심각도(상/중/하)를 한국어 목록으로 정리해줘. "
        "파손이 없으면 '파손 없음'이라고만 답해."
    ),
    "이미지 전체 설명": "이 이미지에 보이는 장면을 한국어로 자세히 설명해줘.",
    "객체 목록 뽑기": (
        "이 이미지에 있는 주요 객체를 한국어 목록으로 나열하고, "
        "가능하면 각 객체의 개수도 함께 알려줘."
    ),
    "이상 상황 탐지": (
        "이 이미지에서 안전상 위험하거나 비정상으로 보이는 요소가 있으면 "
        "무엇인지/어디인지 알려줘. 특별한 게 없으면 '특이사항 없음'이라고 답해."
    ),
}


def _load_font(size: int):
    """한글이 보이도록 맑은 고딕을 우선 시도, 없으면 기본 폰트."""
    for path in ("malgun.ttf", r"C:\Windows\Fonts\malgun.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _draw_boxes(image, labels):
    """라벨 목록을 이미지에 박스+라벨(+있으면 정밀 마스크)로 그린다. (공용)

    labels: [{"class_name": str, "box_2d": [ymin,xmin,ymax,xmax](0~1000),
              "polygon"?: [[x,y](0~1000), ...]}]
    반환: (그려진 이미지, 요약 마크다운)
    """
    base = image.convert("RGB").copy()
    w, h = base.size
    # 마스크 반투명 채움을 위한 RGBA 오버레이.
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    draw = ImageDraw.Draw(base)
    font = _load_font(max(14, h // 40))

    rows = []
    per_class = {}  # 클래스별 번호 매기기.
    class_color = {}  # 클래스 → 색(같은 클래스는 같은 색).
    drawn = 0
    masks = 0
    for lb in labels:
        box = lb.get("box_2d")
        name = (lb.get("class_name") or "object").strip() or "object"
        if not box or len(box) != 4:
            continue
        ymin, xmin, ymax, xmax = box
        # 0~1000 정규화 좌표 → 픽셀 좌표.
        left, right = xmin / 1000 * w, xmax / 1000 * w
        top, bottom = ymin / 1000 * h, ymax / 1000 * h
        if right <= left or bottom <= top:
            continue
        per_class[name] = per_class.get(name, 0) + 1
        # 다중 클래스 구분: 클래스별로 색을 고정 배정.
        if name not in class_color:
            class_color[name] = _COLORS[len(class_color) % len(_COLORS)]
        color = class_color[name]
        rgb = _hex_to_rgb(color)

        # 정밀 마스크(폴리곤)가 있으면 반투명 채움 + 외곽선.
        poly = lb.get("polygon")
        has_mask = bool(poly and len(poly) >= 3)
        if has_mask:
            pts = [(x / 1000 * w, y / 1000 * h) for x, y in poly]
            odraw.polygon(pts, fill=(*rgb, 90))
            draw.line([*pts, pts[0]], fill=color, width=max(2, h // 300))
            masks += 1

        # 박스는 항상 그린다.
        draw.rectangle([left, top, right, bottom], outline=color, width=max(2, h // 250))

        conf = lb.get("confidence")
        conf_str = f" {conf}%" if isinstance(conf, (int, float)) else ""
        tag = f"{name} {per_class[name]}{conf_str}" + (" ▣" if has_mask else "")
        tb = draw.textbbox((0, 0), tag, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        ly = max(0, top - th - 4)
        draw.rectangle([left, ly, left + tw + 6, ly + th + 4], fill=color)
        draw.text((left + 3, ly + 2), tag, fill="white", font=font)

        drawn += 1
        kind = "마스크" if has_mask else "박스"
        rows.append(f"{drawn}. {name}{conf_str} — {kind} {[round(v) for v in box]}")

    annotated = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    if drawn == 0:
        summary = "그려진 박스가 없습니다."
    else:
        head = f"**총 {drawn}개** (정밀 마스크 {masks}개)" if masks else f"**총 {drawn}개 박스**"
        # 다중 클래스면 클래스별 개수도 한 줄로.
        if len(per_class) > 1:
            head += " · " + ", ".join(f"{k} {v}" for k, v in per_class.items())
        summary = head + "\n\n" + "\n".join(rows)
    return annotated, summary


def analyze(image, preset: str, custom_prompt: str):
    """[모드1] 업로드 이미지 + 프롬프트를 Gemini에 보내 분석 결과를 스트리밍한다."""
    if client is None:
        raise gr.Error("GEMINI_API_KEY 가 없습니다. api-test/.env 를 확인하세요.")
    if image is None:
        raise gr.Error("이미지를 먼저 업로드해주세요.")

    prompt = (custom_prompt or "").strip() or PRESETS.get(preset, "")
    if not prompt:
        raise gr.Error("프리셋을 고르거나 질문을 직접 입력해주세요.")

    partial = ""
    try:
        for chunk in client.models.generate_content_stream(
            model=MODEL, contents=[image, prompt]
        ):
            if chunk.text:
                partial += chunk.text
                yield partial
    except Exception as e:
        raise gr.Error(f"API 오류: {e}") from e


def _parse_boxes(raw: str):
    """모델이 준 JSON 텍스트에서 박스 목록을 안전하게 추출한다."""
    text = (raw or "").strip()
    # 혹시 ```json ... ``` 코드펜스로 감싸져 오면 벗겨낸다.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def parse_targets(target: str) -> list[str]:
    """쉼표로 구분된 대상 문자열 → 클래스 목록(중복/공백 제거, 순서 유지)."""
    seen = []
    for t in (target or "").split(","):
        t = t.strip()
        if t and t not in seen:
            seen.append(t)
    return seen


def _detect_labels(image, target: str):
    """Gemini로 대상 박스를 탐지해 라벨 목록을 반환(그리기 없음, detect/배치 공용).

    target은 쉼표로 여러 클래스 지정 가능(예: "포트홀, 균열").
    반환: [{"class_name": str, "box_2d": [...](0~1000), "confidence": int(0~100)}]
    네트워크/한도 오류는 그대로 raise(호출부에서 처리).
    """
    if client is None:
        raise gr.Error("GEMINI_API_KEY 가 없습니다. api-test/.env 를 확인하세요.")

    targets = parse_targets(target)
    if not targets:
        return []
    single = len(targets) == 1
    quoted = ", ".join(f"'{t}'" for t in targets)

    # Gemini 좌표 규약: [ymin, xmin, ymax, xmax], 0~1000 정규화.
    # 실험 결과(중요): "모든 객체 나열"은 배경까지 쏟아내고 라벨 언어가 흔들린다.
    # → 대상만 집중 탐지 + 라벨을 주어진 단어로 고정(enum) + temperature=0.
    box_rule = (
        'each element is {"box_2d":[ymin,xmin,ymax,xmax]} normalized to 0-1000 integers, '
        'plus "confidence": an integer 0-100 (how sure you are this is the target). '
    )
    if single:
        t = targets[0]
        prompt = (
            f"You are an object detector. Detect ONLY '{t}' in this image - nothing else. "
            f"Return a JSON array; {box_rule}"
            f"Include every clearly visible {t}. "
            f"Do NOT return boxes for anything that is not {t}. "
            f"Return [] only if there are truly no {t}."
        )
    else:
        prompt = (
            f"You are an object detector. Detect ONLY these target classes: {quoted}. "
            f'Return a JSON array; each element is {{"box_2d":[ymin,xmin,ymax,xmax]}} '
            f'normalized to 0-1000 integers, plus "label" (EXACTLY one of: {quoted}) '
            f'and "confidence": an integer 0-100. '
            f"Include every clearly visible instance of any target class. "
            f"Use the label value verbatim from the given list - do not translate or invent new labels. "
            f"Ignore anything not in the target list. Return [] if none are present."
        )

    item_props = {
        "box_2d": {"type": "ARRAY", "items": {"type": "INTEGER"}},
        "confidence": {"type": "INTEGER"},
    }
    required = ["box_2d"]
    if not single:
        item_props["label"] = {"type": "STRING", "enum": targets}
        required.append("label")

    schema = {
        "type": "ARRAY",
        "items": {"type": "OBJECT", "properties": item_props, "required": required},
    }

    resp = client.models.generate_content(
        model=MODEL,
        contents=[image, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0,  # 같은 이미지엔 같은 결과가 나오도록 고정.
        ),
    )
    boxes = _parse_boxes(resp.text)

    labels = []
    for item in boxes:
        if not isinstance(item, dict) or len(item.get("box_2d") or []) != 4:
            continue
        if single:
            name = targets[0]
        else:
            name = item.get("label")
            if name not in targets:  # 환각 클래스 제거.
                continue
        lb = {"class_name": name, "box_2d": [round(v) for v in item["box_2d"]]}
        conf = item.get("confidence")
        if isinstance(conf, (int, float)):
            lb["confidence"] = max(0, min(100, int(round(conf))))
        labels.append(lb)
    return labels


def filter_by_confidence(labels, min_conf: int):
    """confidence가 min_conf 미만인 라벨 제거. confidence 없는 라벨은 통과(보수적)."""
    if not min_conf or min_conf <= 0:
        return labels
    return [lb for lb in labels if lb.get("confidence", 100) >= min_conf]


def _is_quota_error(msg: str) -> bool:
    return "RESOURCE_EXHAUSTED" in msg or "429" in msg


def _parse_retry_delay(msg: str, default: float = 8.0) -> float:
    """429 메시지에서 권장 재시도 대기(초)를 뽑는다. 못 찾으면 default."""
    m = re.search(r"retry in ([\d.]+)s", msg) or re.search(r"retryDelay'?:?\s*'?(\d+)s", msg)
    if m:
        try:
            return min(60.0, float(m.group(1)) + 1.0)  # 여유 1초, 최대 60초.
        except ValueError:
            pass
    return default


def _detect_with_retry(image, target: str, max_retries: int = 2):
    """429면 권장 시간만큼 기다렸다 재시도한다(배치 견고성). 그 외 오류는 즉시 전파."""
    for attempt in range(max_retries + 1):
        try:
            return _detect_labels(image, target)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if not _is_quota_error(msg) or attempt == max_retries:
                raise
            time.sleep(_parse_retry_delay(msg))
    return []  # 도달하지 않음.


def detect(image, target: str, min_conf: int = 0):
    """[모드2] 찾을 대상(쉼표로 다중 클래스)을 탐지하고 confidence로 거른 뒤 그린다."""
    if image is None:
        raise gr.Error("이미지를 먼저 업로드해주세요.")
    if not parse_targets(target):
        raise gr.Error("찾을 대상을 입력해주세요. 예: 포트홀  또는  포트홀, 균열")

    try:
        labels = _detect_labels(image, target)
    except gr.Error:
        raise
    except Exception as e:
        # 무료 티어는 분당/일일 요청 한도가 있어 429 가 흔하다.
        msg = str(e)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            raise gr.Error("무료 사용 한도 초과 — 약 10~30초 뒤 다시 시도하세요.") from e
        raise gr.Error(f"API 오류: {msg}") from e

    found = len(labels)
    labels = filter_by_confidence(labels, min_conf)
    dropped = found - len(labels)

    w, h = image.convert("RGB").size
    if not labels:
        annotated = image.convert("RGB").copy()
        extra = f" (신뢰도 {min_conf}% 미만 {dropped}개 제외됨)" if dropped else ""
        summary = f"표시할 객체가 없습니다.{extra}"
    else:
        annotated, summary = _draw_boxes(image, labels)
        if dropped:
            summary += f"\n\n_(신뢰도 {min_conf}% 미만 {dropped}개 제외됨)_"

    record = LabelRecord(
        image_filename=getattr(image, "filename", None) or "image.png",
        image_width=w,
        image_height=h,
        labels=labels,
    )
    return annotated, summary, record, labels_to_rows(labels)


# 수동 보정용 표 헤더(좌표는 0~1000 정규화, conf는 0~100 선택값).
TABLE_HEADERS = ["클래스", "ymin", "xmin", "ymax", "xmax", "conf"]


def labels_to_rows(labels):
    """라벨 목록 → 표 행(편집 가능한 Dataframe용)."""
    return [[lb["class_name"], *lb["box_2d"], lb.get("confidence", "")] for lb in labels]


def _rows_from_table(table):
    """Gradio Dataframe 값(pandas/dict/list)을 행 리스트로 통일."""
    if table is None:
        return []
    if hasattr(table, "values"):  # pandas.DataFrame
        return table.values.tolist()
    if isinstance(table, dict) and "data" in table:
        return table["data"]
    return list(table)


def apply_edits(table, image):
    """표에서 고친 박스를 검증·정리해 다시 그리고, 레코드/표를 갱신한다.

    탐지를 거치지 않고 표에 직접 입력해도 동작한다(순수 수동 라벨링).
    """
    if image is None:
        raise gr.Error("이미지를 먼저 업로드해주세요.")

    labels = []
    for row in _rows_from_table(table):
        if row is None or len(row) < 5:
            continue
        name = "" if row[0] is None else str(row[0]).strip()
        if not name:
            continue  # 클래스명이 비면 무시(빈 행 추가 대비).
        try:
            coords = [int(round(float(v))) for v in row[1:5]]
        except (TypeError, ValueError):
            continue  # 숫자가 아니면 건너뜀.
        coords = [max(0, min(1000, c)) for c in coords]  # 0~1000으로 클램프.
        ymin, xmin, ymax, xmax = coords
        if ymax <= ymin or xmax <= xmin:
            continue  # 면적이 없는 박스 제외.
        lb = {"class_name": name, "box_2d": [ymin, xmin, ymax, xmax]}
        # conf 열(6번째)이 숫자면 confidence로 보존.
        if len(row) >= 6 and row[5] not in (None, ""):
            try:
                lb["confidence"] = max(0, min(100, int(round(float(row[5])))))
            except (TypeError, ValueError):
                pass
        labels.append(lb)

    annotated, summary = _draw_boxes(image, labels)
    w, h = image.convert("RGB").size
    record = LabelRecord(
        image_filename=getattr(image, "filename", None) or "image.png",
        image_width=w,
        image_height=h,
        labels=labels,
    )
    # 정리된 결과로 표도 다시 동기화(잘못된 행 제거 반영).
    return annotated, summary, record, labels_to_rows(labels)


def refine_masks(record: LabelRecord | None, image):
    """[정밀화] 현재 박스들을 SAM으로 픽셀 마스크(폴리곤)로 정밀화해 다시 그린다."""
    if image is None:
        raise gr.Error("이미지를 먼저 업로드해주세요.")
    if not record or not record.labels:
        raise gr.Error("정밀화할 박스가 없습니다. 먼저 '박스로 찾기' 또는 수동 입력을 하세요.")

    new_labels, msg = segmenter.segment_labels(image, record.labels)
    annotated, draw_summary = _draw_boxes(image, new_labels)
    w, h = image.convert("RGB").size
    new_record = LabelRecord(
        image_filename=record.image_filename,
        image_width=w,
        image_height=h,
        labels=new_labels,
    )
    summary = f"🎯 {msg}\n\n{draw_summary}"
    return annotated, summary, new_record, labels_to_rows(new_labels)


def load_labels(file, image, target: str):
    """[불러오기] 저장된 라벨 파일을 읽어 표/이미지에 복원한다(이어서 작업).

    지원: 우리 meta.json(완전 복원) · COCO json · YOLO txt.
    YOLO는 클래스 이름이 없으므로 '찾을 대상'(쉼표 목록)을 id 순서로 사용한다.
    그리기에는 업로드된 이미지가 필요하다.
    """
    if image is None:
        raise gr.Error("라벨을 그릴 이미지를 먼저 업로드해주세요.")
    path = file if isinstance(file, str) else getattr(file, "name", None)
    if not path or not os.path.exists(path):
        raise gr.Error("라벨 파일을 올려주세요 (.json COCO/meta 또는 .txt YOLO).")

    with open(path, encoding="utf-8") as f:
        raw = f.read()

    try:
        if path.lower().endswith(".json"):
            data = json.loads(raw)
            if isinstance(data, dict) and "labels" in data:  # 우리 meta.json
                labels = from_record_dict(data).labels
            elif isinstance(data, dict) and "annotations" in data:  # COCO
                labels = from_coco(data).labels
            else:
                raise gr.Error("알 수 없는 JSON 형식입니다 (meta.json 또는 COCO).")
        else:  # YOLO txt
            labels = from_yolo(raw, parse_targets(target))
    except gr.Error:
        raise
    except Exception as e:  # noqa: BLE001
        raise gr.Error(f"라벨 파일을 읽지 못했습니다: {e}") from e

    annotated, draw_summary = _draw_boxes(image, labels)
    w, h = image.convert("RGB").size
    record = LabelRecord(
        image_filename=getattr(image, "filename", None) or os.path.basename(path),
        image_width=w,
        image_height=h,
        labels=labels,
    )
    summary = f"📂 라벨 {len(labels)}개 불러옴.\n\n{draw_summary}"
    return annotated, summary, record, labels_to_rows(labels)


def export_labels(record: LabelRecord | None, fmt: str):
    """현재 라벨 레코드를 선택한 형식의 파일로 만들어 다운로드 경로를 돌려준다."""
    if not record or not record.labels:
        raise gr.Error("내보낼 라벨이 없습니다. 먼저 '박스로 찾기'를 실행하세요.")

    base = os.path.splitext(record.image_filename)[0] or "labels"
    tmp = tempfile.mkdtemp(prefix="labels_")
    cls_path = os.path.join(tmp, "classes.txt")
    with open(cls_path, "w", encoding="utf-8") as f:
        f.write(yolo_classes_txt(record))

    if fmt == "YOLO":
        path = os.path.join(tmp, f"{base}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(to_yolo(record))
        return [path, cls_path]
    if fmt == "YOLO-seg":
        path = os.path.join(tmp, f"{base}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(to_yolo_seg(record))  # 폴리곤 없으면 박스 꼭짓점으로 대체.
        return [path, cls_path]
    # COCO (polygon 있으면 segmentation 자동 포함)
    path = os.path.join(tmp, f"{base}.coco.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_coco_json(record))
    return [path]


def save_to_backend(record: LabelRecord | None, annotated):
    """라벨링 결과를 백엔드(현재 MOCK)에 저장하고 상태 메시지를 돌려준다."""
    resp = backend_client.save_labeling(record, annotated)
    if resp["status"] != "ok":
        return f"❌ {resp['message']}"
    return (
        f"✅ {resp['message']}\n\n"
        f"- backend: `{resp['backend']}`\n"
        f"- record_id: `{resp['record_id']}`\n"
        f"- 저장 위치: `{resp['saved_path']}`"
    )


def batch_process(
    files, target: str, save_backend: bool, use_mask: bool = False,
    delay: float = 4.0, min_conf: int = 0,
):
    """[모드3] 여러 이미지를 한 번에 자동 라벨링한다.

    target은 쉼표로 다중 클래스 지정 가능. min_conf 미만 박스는 제외.
    각 이미지: Gemini 탐지(429면 자동 재시도) → confidence 필터 → (옵션)SAM 마스크 →
    YOLO/COCO 저장 → (옵션)mock 백엔드 저장. 한 장이 실패해도 멈추지 않는다.
    호출 사이에 `delay`초 쉬어 무료 티어 한도(429)를 완화한다.
    반환: (결과 표, zip 경로, 요약 마크다운)
    """
    targets = parse_targets(target)
    if not files:
        raise gr.Error("이미지 파일을 먼저 올려주세요.")
    if not targets:
        raise gr.Error("찾을 대상을 입력해주세요. 예: 포트홀  또는  포트홀, 균열")

    # 배치 전체에서 클래스 id를 일관되게 쓰도록 전역 클래스맵 고정(이미지마다 달라지면 안 됨).
    global_cmap = {name: i for i, name in enumerate(targets)}

    out_dir = tempfile.mkdtemp(prefix="batch_")
    rows = []
    ok = 0
    total_boxes = 0
    total_masks = 0
    total_dropped = 0
    n = len(files)
    for idx, fpath in enumerate(files):
        # gr.File(multiple)은 임시 경로(str) 또는 .name 객체로 올 수 있다.
        path = fpath if isinstance(fpath, str) else getattr(fpath, "name", str(fpath))
        name = os.path.basename(path)
        try:
            image = Image.open(path)
            image.filename = name
            labels = _detect_with_retry(image, target)

            before = len(labels)
            labels = filter_by_confidence(labels, min_conf)
            total_dropped += before - len(labels)

            masks_here = 0
            if use_mask and labels:
                labels, _ = segmenter.segment_labels(image, labels)
                masks_here = sum(1 for lb in labels if lb.get("polygon"))

            w, h = image.convert("RGB").size
            record = LabelRecord(name, w, h, labels)

            stem = os.path.splitext(name)[0] or name
            # 마스크가 있으면 YOLO-seg 로 저장(없으면 박스 꼭짓점으로 자동 대체). 전역 클래스맵 사용.
            with open(os.path.join(out_dir, f"{stem}.txt"), "w", encoding="utf-8") as f:
                f.write(
                    to_yolo_seg(record, global_cmap) if use_mask else to_yolo(record, global_cmap)
                )
            with open(os.path.join(out_dir, f"{stem}.coco.json"), "w", encoding="utf-8") as f:
                json.dump(to_coco(record, global_cmap), f, ensure_ascii=False, indent=2)

            status = f"완료(마스크 {masks_here})" if use_mask else "완료"
            if save_backend:
                annotated = (
                    _draw_boxes(image, labels)[0] if labels else image.convert("RGB").copy()
                )
                resp = backend_client.save_labeling(record, annotated)
                status = "저장됨" + (f"(마스크 {masks_here})" if use_mask else "")
                if resp["status"] != "ok":
                    status = "저장실패"

            rows.append([name, len(labels), status])
            total_boxes += len(labels)
            total_masks += masks_here
            ok += 1
        except Exception as e:  # noqa: BLE001 - 배치는 한 장 실패로 멈추면 안 됨.
            msg = str(e)
            short = "한도초과(429)" if _is_quota_error(msg) else msg[:60]
            rows.append([name, 0, f"오류: {short}"])

        # 다음 장이 남았으면 호출 간 딜레이(429 완화). SAM은 로컬이라 무관.
        if idx < n - 1 and delay and delay > 0:
            time.sleep(delay)

    # 공통 클래스 파일(전역 클래스맵 = id 순서).
    with open(os.path.join(out_dir, "classes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(targets))

    zip_base = os.path.join(tempfile.mkdtemp(prefix="batchzip_"), "labels_batch")
    zip_path = shutil.make_archive(zip_base, "zip", out_dir)

    extra = []
    if len(targets) > 1:
        extra.append("클래스 " + ", ".join(targets))
    if use_mask:
        extra.append(f"정밀 마스크 {total_masks}개")
    if total_dropped:
        extra.append(f"신뢰도 {min_conf}%미만 {total_dropped}개 제외")
    if save_backend:
        extra.append("mock 백엔드 저장됨")
    summary = f"**{ok}/{n}장 처리 완료 · 박스 총 {total_boxes}개**" + (
        "\n\n(" + " · ".join(extra) + ")" if extra else ""
    )
    return rows, zip_path, summary


def build_dashboard():
    """저장된 라벨(_saved/) 전체를 집계해 요약·차트·이미지별 표를 만든다."""
    import pandas as pd

    records = stats.load_saved_records(backend_client._SAVE_ROOT)
    agg = stats.aggregate(records)

    if agg["n_images"] == 0:
        empty_c = pd.DataFrame({"클래스": [], "개수": []})
        empty_h = pd.DataFrame({"신뢰도 구간": stats.CONF_BINS, "개수": [0] * len(stats.CONF_BINS)})
        return "저장된 라벨이 없습니다. 먼저 '백엔드에 저장' 또는 배치로 저장하세요.", empty_c, empty_h, []

    md = (
        f"**이미지 {agg['n_images']}장 · 라벨 {agg['n_labels']}개 · "
        f"클래스 {agg['n_classes']}종 · 정밀 마스크 {agg['mask_labels']}개**\n\n"
        f"- 이미지당 평균 박스: **{agg['avg_boxes']}개**\n"
        f"- 신뢰도 기록된 라벨: {agg['n_conf']}개"
    )

    cc = agg["class_counts"]
    class_df = pd.DataFrame(
        {"클래스": list(cc.keys()), "개수": list(cc.values())}
    ).sort_values("개수", ascending=False)

    ch = agg["conf_hist"]
    conf_df = pd.DataFrame({"신뢰도 구간": list(ch.keys()), "개수": list(ch.values())})

    table = [[d["image"], d["boxes"]] for d in agg["boxes_per_image"]]
    return md, class_df, conf_df, table


with gr.Blocks(title="이미지 이해·라벨링 데모") as demo:
    gr.Markdown(
        f"# 🖼️ 이미지 이해·라벨링 데모\n"
        f"모델: `{MODEL}` (무료 티어) · Gemini 멀티모달로 이미지를 분석합니다."
    )

    with gr.Tabs():
        with gr.Tab("📝 설명 분석"):
            with gr.Row():
                with gr.Column():
                    image_in = gr.Image(type="pil", label="이미지 업로드")
                    preset_in = gr.Dropdown(
                        choices=list(PRESETS.keys()),
                        value="도로 파손/포트홀 찾기",
                        label="분석 시나리오 (프리셋)",
                    )
                    custom_in = gr.Textbox(
                        label="직접 질문 (선택) — 입력하면 프리셋 대신 이게 쓰임",
                        placeholder="예: 이 사진에서 보행자에게 위험한 요소를 찾아줘",
                        lines=2,
                    )
                    run_btn = gr.Button("분석하기", variant="primary")
                with gr.Column():
                    output = gr.Markdown(label="분석 결과")
            run_btn.click(analyze, inputs=[image_in, preset_in, custom_in], outputs=output)

        with gr.Tab("🔲 박스로 찾기"):
            gr.Markdown(
                "찾을 대상을 입력하면 Gemini가 위치를 추정해 **박스 + 라벨**을 그려줍니다. "
                "쉼표로 **여러 클래스 동시 탐지**(예: `포트홀, 균열`)가 가능하고, "
                "**신뢰도 필터**로 애매한 박스를 걸러낼 수 있어요."
            )
            with gr.Row():
                with gr.Column():
                    det_image_in = gr.Image(type="pil", label="이미지 업로드")
                    target_in = gr.Textbox(
                        label="찾을 대상 (쉼표로 여러 개)",
                        value="포트홀",
                        placeholder="예: 포트홀  또는  포트홀, 균열, 맨홀",
                    )
                    conf_in = gr.Slider(
                        minimum=0, maximum=100, value=0, step=5,
                        label="신뢰도 필터 (이 % 미만 박스 제외, 0=끄기)",
                    )
                    det_btn = gr.Button("박스로 찾기", variant="primary")
                with gr.Column():
                    det_image_out = gr.Image(type="pil", label="결과 (박스 표시)")
                    det_summary = gr.Markdown()

            # 라벨 레코드를 탭 내에서 들고 있다가 수정/내보내기/저장에 재사용.
            det_state = gr.State(value=None)

            gr.Markdown(
                "### ✏️ 수동 보정 (박스 추가 / 수정 / 삭제)\n"
                "표에서 좌표(**0~1000 정규화**, `ymin·xmin·ymax·xmax`)나 클래스명을 고치고, "
                "행을 추가/삭제한 뒤 **[수정 반영]**을 누르세요. "
                "탐지를 건너뛰고 표에 직접 입력해 **수동 라벨링**도 가능합니다."
            )
            det_table = gr.Dataframe(
                headers=TABLE_HEADERS,
                datatype=["str", "number", "number", "number", "number", "number"],
                row_count=(0, "dynamic"),
                column_count=(6, "fixed"),
                label="라벨 박스 (편집 가능 · conf는 신뢰도 0~100)",
            )
            with gr.Row():
                apply_btn = gr.Button("✏️ 수정 반영 (다시 그리기)")
                refine_btn = gr.Button("🎯 정밀 마스크 (SAM)", variant="secondary")

            gr.Markdown(
                "### 📂 라벨 불러오기 (이어서 작업)\n"
                "이전에 저장한 `meta.json`/COCO `.json`/YOLO `.txt`를 올리면 표·이미지에 복원됩니다. "
                "(이미지를 먼저 업로드한 뒤 불러오세요. YOLO는 위 '찾을 대상' 순서를 클래스로 사용)"
            )
            with gr.Row():
                load_file = gr.File(
                    file_count="single",
                    file_types=[".json", ".txt"],
                    label="라벨 파일",
                )
                load_btn = gr.Button("📂 불러오기")

            gr.Markdown("### 💾 라벨 내보내기 / 저장")
            with gr.Row():
                fmt_in = gr.Radio(
                    choices=["YOLO", "YOLO-seg", "COCO"],
                    value="YOLO",
                    label="내보내기 형식 (YOLO-seg/COCO는 마스크 폴리곤 포함)",
                )
                export_btn = gr.Button("라벨 파일 만들기")
                save_btn = gr.Button("백엔드에 저장 (mock)", variant="primary")
            export_files = gr.File(label="다운로드", file_count="multiple")
            save_status = gr.Markdown()

            det_btn.click(
                detect,
                inputs=[det_image_in, target_in, conf_in],
                outputs=[det_image_out, det_summary, det_state, det_table],
            )
            apply_btn.click(
                apply_edits,
                inputs=[det_table, det_image_in],
                outputs=[det_image_out, det_summary, det_state, det_table],
            )
            refine_btn.click(
                refine_masks,
                inputs=[det_state, det_image_in],
                outputs=[det_image_out, det_summary, det_state, det_table],
            )
            load_btn.click(
                load_labels,
                inputs=[load_file, det_image_in, target_in],
                outputs=[det_image_out, det_summary, det_state, det_table],
            )
            export_btn.click(
                export_labels,
                inputs=[det_state, fmt_in],
                outputs=export_files,
            )
            save_btn.click(
                save_to_backend,
                inputs=[det_state, det_image_out],
                outputs=save_status,
            )

        with gr.Tab("📁 배치 처리"):
            gr.Markdown(
                "여러 이미지를 **한 번에 자동 라벨링**합니다. 찾을 대상을 입력하고 이미지들을 "
                "올린 뒤 실행하면, 각 이미지의 YOLO/COCO 라벨을 만들어 zip으로 묶어줍니다. "
                "한 장이 실패해도 멈추지 않고 끝까지 처리합니다."
            )
            with gr.Row():
                with gr.Column():
                    batch_files = gr.File(
                        file_count="multiple",
                        file_types=["image"],
                        label="이미지들 (여러 장 선택)",
                    )
                    batch_target = gr.Textbox(
                        label="찾을 대상 (쉼표로 여러 개)",
                        value="포트홀",
                        placeholder="예: 포트홀  또는  포트홀, 균열, 맨홀",
                    )
                    batch_conf = gr.Slider(
                        minimum=0, maximum=100, value=0, step=5,
                        label="신뢰도 필터 (이 % 미만 박스 제외, 0=끄기)",
                    )
                    batch_save = gr.Checkbox(label="mock 백엔드에도 저장", value=True)
                    batch_mask = gr.Checkbox(
                        label="🎯 정밀 마스크(SAM)도 적용 (로컬, 한도 무관·느림)", value=False
                    )
                    batch_delay = gr.Slider(
                        minimum=0, maximum=15, value=4, step=1,
                        label="Gemini 호출 간 딜레이(초) — 429 한도 완화",
                    )
                    batch_btn = gr.Button("배치 라벨링 실행", variant="primary")
                with gr.Column():
                    batch_summary = gr.Markdown()
                    batch_table = gr.Dataframe(
                        headers=["파일", "박스수", "상태"],
                        datatype=["str", "number", "str"],
                        label="처리 결과",
                        interactive=False,
                    )
                    batch_zip = gr.File(label="라벨 묶음 다운로드 (zip)")
            batch_btn.click(
                batch_process,
                inputs=[batch_files, batch_target, batch_save, batch_mask, batch_delay, batch_conf],
                outputs=[batch_table, batch_zip, batch_summary],
            )

        with gr.Tab("📊 통계 대시보드"):
            gr.Markdown(
                "지금까지 **백엔드에 저장(`_saved/`)** 된 라벨 전체를 집계합니다. "
                "라벨링 작업 현황·데이터 품질을 한눈에 볼 수 있어요."
            )
            dash_btn = gr.Button("📊 통계 새로고침", variant="primary")
            dash_summary = gr.Markdown()
            with gr.Row():
                dash_class = gr.BarPlot(
                    x="클래스", y="개수", title="클래스별 라벨 수", color="클래스",
                )
                dash_conf = gr.BarPlot(
                    x="신뢰도 구간", y="개수", title="신뢰도 분포",
                )
            dash_table = gr.Dataframe(
                headers=["이미지", "박스수"],
                datatype=["str", "number"],
                label="이미지별 박스 수",
                interactive=False,
            )
            dash_btn.click(
                build_dashboard,
                outputs=[dash_summary, dash_class, dash_conf, dash_table],
            )

if __name__ == "__main__":
    demo.launch()
