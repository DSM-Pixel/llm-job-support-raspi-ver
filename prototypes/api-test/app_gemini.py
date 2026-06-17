"""Google Gemini 연동 확인용 최소 Gradio 채팅 데모 (무료 티어).

데모 시나리오: "키를 넣고 앱을 띄우면 Gemini와 한국어로 대화가 된다."
app.py(Claude 버전)의 Gemini 짝꿍. 연동 검증용이라 기능은 일부러 최소.

실행:
    python prototypes/api-test/app_gemini.py
실행 후 출력되는 http://127.0.0.1:7860 주소를 브라우저에서 연다.
"""

import os

import gradio as gr
from dotenv import load_dotenv
from google import genai

DEFAULT_MODEL = "gemini-2.5-flash"

here = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(here, ".env"))
load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=_api_key) if _api_key else None


def respond(message: str, history: list[dict]):
    """사용자 메시지를 받아 Gemini 응답을 스트리밍으로 돌려준다."""
    if client is None:
        raise gr.Error("GEMINI_API_KEY 가 설정되지 않았습니다. .env 파일을 확인하세요.")
    if not message.strip():
        raise gr.Error("메시지를 입력해주세요.")

    # Gradio messages 형식(history)을 Gemini contents 형식으로 변환.
    # Gemini 는 assistant 역할을 "model" 로 부른다.
    contents = []
    for m in history:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    partial = ""
    try:
        for chunk in client.models.generate_content_stream(model=MODEL, contents=contents):
            if chunk.text:
                partial += chunk.text
                yield partial
    except Exception as e:  # SDK 예외 계층이 환경마다 달라 메시지로 안내.
        raise gr.Error(f"API 오류: {e}") from e


demo = gr.ChatInterface(
    fn=respond,
    title="Gemini API 연동 테스트",
    description=f"모델: {MODEL} · 무료 티어 · 키가 없으면 .env 를 먼저 설정하세요.",
    examples=["안녕? 한 문장으로 자기소개 해줘.", "포트홀 라벨링 자동화가 뭔지 쉽게 설명해줘."],
)

if __name__ == "__main__":
    demo.launch()
