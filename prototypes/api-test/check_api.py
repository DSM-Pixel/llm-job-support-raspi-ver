"""Claude API 연동 스모크 테스트.

API 키가 제대로 설정됐는지, 실제로 응답이 오는지 한 번에 확인하는 최소 스크립트.
Gradio 같은 UI 없이 터미널에서 바로 돌려본다.

실행:
    uv run python prototypes/api-test/check_api.py
    # 또는
    python prototypes/api-test/check_api.py
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

# 기본 모델 — claude-api 가이드 기준 최신 Opus.
DEFAULT_MODEL = "claude-opus-4-8"


def main() -> int:
    # prototypes/api-test/.env 를 우선 읽고, 없으면 현재 폴더의 .env 도 시도.
    here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(here, ".env"))
    load_dotenv()  # 프로젝트 루트에서 실행한 경우 대비

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[X] ANTHROPIC_API_KEY 가 없습니다.")
        print("    prototypes/api-test/.env.example 를 복사해 .env 를 만들고 키를 넣으세요.")
        return 1

    model = os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic()  # 환경변수에서 키를 자동으로 읽음

    print(f"[*] 모델 {model} 로 연결 테스트 중...")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": "연결 테스트야. '연결 성공'이라고 한 문장으로만 답해줘.",
                }
            ],
        )
    except anthropic.AuthenticationError:
        print("[X] 인증 실패 — API 키가 잘못됐거나 만료됐습니다.")
        return 1
    except anthropic.NotFoundError:
        print(f"[X] 모델 '{model}' 을(를) 찾을 수 없습니다. 모델 이름을 확인하세요.")
        return 1
    except anthropic.RateLimitError:
        print("[X] 요청 한도 초과 — 잠시 후 다시 시도하세요.")
        return 1
    except anthropic.APIConnectionError:
        print("[X] 네트워크 오류 — 인터넷 연결/프록시를 확인하세요.")
        return 1
    except anthropic.APIStatusError as e:
        print(f"[X] API 오류 ({e.status_code}): {e.message}")
        return 1

    text = next((b.text for b in response.content if b.type == "text"), "")
    usage = response.usage

    print("[O] 연결 성공!")
    print(f"    응답  : {text.strip()}")
    print(f"    토큰  : 입력 {usage.input_tokens} / 출력 {usage.output_tokens}")
    print(f"    요청ID: {response._request_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
