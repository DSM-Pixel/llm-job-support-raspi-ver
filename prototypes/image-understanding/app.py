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

import gradio as gr
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

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


def detect(image, target: str):
    """[모드2] 찾을 대상의 바운딩 박스를 받아 이미지에 박스+라벨을 그린다."""
    if client is None:
        raise gr.Error("GEMINI_API_KEY 가 없습니다. api-test/.env 를 확인하세요.")
    if image is None:
        raise gr.Error("이미지를 먼저 업로드해주세요.")
    target = (target or "").strip()
    if not target:
        raise gr.Error("찾을 대상을 입력해주세요. 예: 포트홀, 차량, 사람, 표지판")

    # Gemini 좌표 규약: [ymin, xmin, ymax, xmax], 0~1000 정규화.
    # 실험 결과(중요): "모든 객체를 나열"시키면 배경(도로/벽/나무)까지 쏟아내고,
    # 라벨 언어도 실행마다 흔들려(포트홀↔pothole↔도로 파손) 매칭이 깨진다.
    # 가장 안정적인 건 "대상만 집중 탐지 + 라벨은 사용자 단어로 고정 + temperature=0".
    prompt = (
        f"You are an object detector. Detect ONLY '{target}' in this image - nothing else. "
        'Return a JSON array; each element is {"box_2d":[ymin,xmin,ymax,xmax]} '
        f"normalized to 0-1000 integers, one box per detected {target}. "
        f"Include every clearly visible {target}. "
        f"Do NOT return boxes for road, wall, sky, trees, people, stones or anything that is not {target}. "
        f"Return [] only if there are truly no {target} in the image."
    )

    # box_2d 만 받는 구조화 출력. 라벨은 코드에서 대상 단어로 통일한다.
    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {"box_2d": {"type": "ARRAY", "items": {"type": "INTEGER"}}},
            "required": ["box_2d"],
        },
    }

    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0,  # 같은 이미지엔 같은 결과가 나오도록 고정.
            ),
        )
    except Exception as e:
        # 무료 티어는 분당/일일 요청 한도가 있어 429 가 흔하다.
        msg = str(e)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            raise gr.Error("무료 사용 한도 초과 — 약 10~30초 뒤 다시 시도하세요.") from e
        raise gr.Error(f"API 오류: {msg}") from e

    boxes = _parse_boxes(resp.text)

    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    w, h = annotated.size
    font = _load_font(max(14, h // 40))

    rows = []
    drawn = 0
    for i, item in enumerate(boxes):
        box = item.get("box_2d") if isinstance(item, dict) else None
        if not box or len(box) != 4:
            continue
        # 라벨은 사용자가 찾는 단어로 통일(번호를 붙여 구분).
        label = target
        ymin, xmin, ymax, xmax = box
        # 0~1000 정규화 좌표 → 픽셀 좌표.
        left, right = xmin / 1000 * w, xmax / 1000 * w
        top, bottom = ymin / 1000 * h, ymax / 1000 * h
        if right <= left or bottom <= top:
            continue
        color = _COLORS[drawn % len(_COLORS)]
        draw.rectangle([left, top, right, bottom], outline=color, width=max(2, h // 250))

        # 라벨 배경 + 텍스트(같은 대상이 여러 개면 번호로 구분).
        tag = f"{label} {drawn + 1}"
        tb = draw.textbbox((0, 0), tag, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        ly = max(0, top - th - 4)
        draw.rectangle([left, ly, left + tw + 6, ly + th + 4], fill=color)
        draw.text((left + 3, ly + 2), tag, fill="white", font=font)

        drawn += 1
        rows.append(f"{drawn}. {label} — 박스 {[round(v) for v in box]}")

    if drawn == 0:
        summary = f"'{target}' 에 해당하는 객체를 찾지 못했습니다."
    else:
        summary = f"**'{target}' {drawn}개 발견**\n\n" + "\n".join(rows)

    return annotated, summary


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
                "라벨링 자동화의 미리보기 단계예요."
            )
            with gr.Row():
                with gr.Column():
                    det_image_in = gr.Image(type="pil", label="이미지 업로드")
                    target_in = gr.Textbox(
                        label="찾을 대상",
                        value="포트홀",
                        placeholder="예: 포트홀, 차량, 사람, 표지판, 균열",
                    )
                    det_btn = gr.Button("박스로 찾기", variant="primary")
                with gr.Column():
                    det_image_out = gr.Image(type="pil", label="결과 (박스 표시)")
                    det_summary = gr.Markdown()
            det_btn.click(
                detect,
                inputs=[det_image_in, target_in],
                outputs=[det_image_out, det_summary],
            )

if __name__ == "__main__":
    demo.launch()
