"""Claude API 연동 확인용 최소 Gradio 채팅 데모.

데모 시나리오: "키를 넣고 앱을 띄우면 Claude와 한국어로 대화가 된다."
연동만 검증하는 용도라 기능은 일부러 최소로 유지. 여기서부터 팀별 기능을 붙여나간다.

실행:
    uv run --extra demo python prototypes/api-test/app.py
    # 또는 (gradio 설치돼 있으면)
    python prototypes/api-test/app.py
"""

import os

import anthropic
import gradio as gr
from dotenv import load_dotenv

DEFAULT_MODEL = "claude-opus-4-8"

here = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(here, ".env"))
load_dotenv()

MODEL = os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
client = anthropic.Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None


def respond(message: str, history: list[dict]):
    """사용자 메시지를 받아 Claude 응답을 스트리밍으로 돌려준다."""
    if client is None:
        raise gr.Error("ANTHROPIC_API_KEY 가 설정되지 않았습니다. .env 파일을 확인하세요.")
    if not message.strip():
        raise gr.Error("메시지를 입력해주세요.")

    # Gradio messages 형식(history)을 그대로 Anthropic messages 형식으로 사용.
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": message})

    partial = ""
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=2048,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                partial += text
                yield partial
    except anthropic.APIStatusError as e:
        raise gr.Error(f"API 오류 ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise gr.Error("네트워크 오류 — 연결을 확인하세요.") from e


demo = gr.ChatInterface(
    fn=respond,
    type="messages",
    title="Claude API 연동 테스트",
    description=f"모델: {MODEL} · 키가 없으면 .env 를 먼저 설정하세요.",
    examples=["안녕? 한 문장으로 자기소개 해줘.", "포트홀 라벨링 자동화가 뭔지 쉽게 설명해줘."],
)

if __name__ == "__main__":
    demo.launch()
