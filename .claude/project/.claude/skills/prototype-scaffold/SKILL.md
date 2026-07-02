---
name: prototype-scaffold
description: Gradio/FastAPI/Streamlit 단일 파일 프로토타입 스캐폴드를 `prototypes/<feature>/` 아래 생성. 시연 시나리오 한 줄과 MOCK 처리 함수로 시작해 점진적으로 실 모델(API)을 끼우게 한다.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
---

# /prototype-scaffold

빠르게 시연 가능한 데모 1파일을 만든다. 이 스킬은 `prototype-builder` 서브에이전트의 컨벤션을 그대로 따른다.

## 입력 수집

사용자가 충분히 안 알려줬다면 `AskUserQuestion`으로:
1. **기능 이름** (kebab-case, 예: `pothole-detect`)
2. **프레임워크**: Gradio (default) / Streamlit / FastAPI(JSON API)
3. **입력**: 이미지 / 텍스트 / 이미지+텍스트 / CSV 업로드 / 공공데이터 API
4. **출력**: 마스크 이미지 / 라벨 JSON / 요약 텍스트 / 차트 / 보고서 마크다운
5. **시연 시나리오 한 줄** (예: "포트홀 영역을 빨갛게 표시해줘")

## 생성물

```
prototypes/<feature>/
├── app.py              # Gradio (또는 FastAPI/Streamlit) 단일 진입점
├── README.md           # 시연 시나리오 + 실행 명령
├── requirements.txt    # uv 안 쓰는 사람용 의존성 목록
└── sample/             # 데모 입력 샘플 자리 (개인정보 없는 것만)
```

## app.py 작성 규칙

- 파일 상단 docstring에 **시연 시나리오 한 줄**을 박는다.
- 핵심 처리 함수는 **MOCK 구현**으로 시작 — 모델 로딩 없이도 UI가 뜨고 결과가 나와야 한다.
- `# TODO(<feature>):` 마커로 실제 모델 연결 위치를 표시.
- **LLM 호출은 어댑터 경유** — 현재 키는 Gemini뿐이므로 `GEMINI_API_KEY` 없으면 MOCK 폴백 (`.claude/rules/api-design.md` 준수). 모델명/키 하드코딩 금지.
- 모델 로딩은 **lazy** (함수 내부 첫 호출 시). RPi5(GPU 없음)에서 못 도는 무거운 로컬 추론을 기본 경로로 넣지 말 것.
- 에러는 `gr.Error("…")` / `HTTPException(400, "…")`처럼 사용자 친화적으로.
- 포트 자동 (`server_port=None`), 호스트는 `127.0.0.1` 기본.

## Gradio 예시 골격

```python
"""<시연 시나리오 한 줄>."""
from __future__ import annotations
import gradio as gr

def run(image, query: str):
    if image is None:
        raise gr.Error("이미지를 먼저 업로드해주세요")
    # TODO(<feature>): 실제 VLM/SAM/RAG 호출 (어댑터 경유, 키 없으면 MOCK)
    return image, f"(mock) 질의='{query}'"

with gr.Blocks(title="<feature>") as demo:
    gr.Markdown("## <feature> 데모")
    with gr.Row():
        img = gr.Image(type="pil", label="입력")
        out = gr.Image(label="결과")
    q = gr.Textbox(label="질의", value="<기본 질의>")
    log = gr.Markdown()
    gr.Button("실행", variant="primary").click(run, [img, q], [out, log])

if __name__ == "__main__":
    demo.launch()
```

## README.md 작성

```markdown
# <feature>

## 시연 시나리오
- "<한 줄 시나리오>"

## 실행
```
uv run python prototypes/<feature>/app.py
# 또는
python -m pip install -r requirements.txt && python prototypes/<feature>/app.py
```

## 의존성
gradio, pillow, (모델 라이브러리 추가 시 여기 적기)

## TODO
- [ ] MOCK 함수를 실제 모델로 교체
- [ ] 샘플 이미지 추가 (sample/)
- [ ] 시연 영상/스크린샷 찍기
```

## 마지막 행동

1. 만든 파일 경로를 한 줄씩 출력.
2. `uv run python prototypes/<feature>/app.py` 실행 명령 안내.
3. "지금 바로 띄워볼까요?"라고 물어 사용자가 Yes면 `Bash`로 실행(백그라운드, 포트 출력만 보고 멈춤).
4. 검증된 프로토타입은 나중에 `backend/`로 이식한다고 안내 (예: `prototypes/rag-search` → `backend/rag_engine.py` 전례).

## 하지 말 것

- 처음부터 패키지화(`__init__.py`, `setup.py`) 하지 말 것.
- 모델 weight 다운로드를 import 시점에 트리거하지 말 것.
- 시연 시나리오 없이 진행하지 말 것.
