"""Google Gemini API 연동 스모크 테스트 (무료 티어용).

Claude 크레딧 없이 'Python에서 LLM API가 실제로 호출되는지' 흐름만
무료로 확인하기 위한 최소 스크립트. check_api.py 의 Gemini 버전이다.

키 발급: https://aistudio.google.com/apikey (구글 로그인, 결제수단 불필요)

실행:
    python prototypes/api-test/check_gemini.py
"""

import os
import sys

from dotenv import load_dotenv
from google import genai

# 무료 티어에서 쓸 수 있는 빠른 기본 모델.
DEFAULT_MODEL = "gemini-2.5-flash"


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(here, ".env"))
    load_dotenv()  # 프로젝트 루트에서 실행한 경우 대비

    # GEMINI_API_KEY 우선, 없으면 GOOGLE_API_KEY 도 시도.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[X] GEMINI_API_KEY 가 없습니다.")
        print("    https://aistudio.google.com/apikey 에서 키를 발급받아")
        print("    prototypes/api-test/.env 에 GEMINI_API_KEY=... 로 넣으세요.")
        return 1

    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    client = genai.Client(api_key=api_key)

    print(f"[*] 모델 {model} 로 연결 테스트 중...")

    try:
        response = client.models.generate_content(
            model=model,
            contents="연결 테스트야. '연결 성공'이라고 한 문장으로만 답해줘.",
        )
    except Exception as e:  # SDK 예외 계층이 환경마다 달라 메시지로 안내.
        msg = str(e)
        if "API_KEY_INVALID" in msg or "API key not valid" in msg:
            print("[X] 인증 실패 — API 키가 잘못됐습니다. 키를 다시 확인하세요.")
        elif "PERMISSION_DENIED" in msg:
            print("[X] 권한 거부 — 키 권한 또는 모델 접근을 확인하세요.")
        elif "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
            print("[X] 무료 한도 초과 — 잠시 후 다시 시도하세요.")
        elif "NOT_FOUND" in msg or "not found" in msg.lower():
            print(f"[X] 모델 '{model}' 을(를) 찾을 수 없습니다. GEMINI_MODEL 값을 확인하세요.")
        else:
            print(f"[X] API 오류: {msg}")
        return 1

    print("[O] 연결 성공!")
    print(f"    응답  : {response.text.strip()}")
    usage = getattr(response, "usage_metadata", None)
    if usage:
        print(
            f"    토큰  : 입력 {usage.prompt_token_count} / "
            f"출력 {usage.candidates_token_count}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
