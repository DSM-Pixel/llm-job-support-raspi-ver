# 이미지 라벨링 데모 — 개발 시작 가이드

이 프로토타입은 **Gemini 멀티모달**로 이미지를 분석/라벨링하는 Gradio 앱입니다.
(`app.py` — 탭 2개: "📝 설명 분석", "🔲 박스로 찾기")

## 1. 사전 준비 (이미 세팅됨)

- 가상환경: `llm-job-support/.venv` (Python 3.13)
- 의존성: `gradio`, `google-genai`, `python-dotenv`, `pillow`, `anthropic`, `ruff`
- VSCode 인터프리터: `.vscode/settings.json`에서 `.venv`로 지정됨

## 2. API 키 입력 (필수)

`prototypes/api-test/.env` 파일을 열어 **GEMINI_API_KEY** 를 채웁니다.

```
GEMINI_API_KEY=여기에_키_붙여넣기
```

- 키 발급(무료): https://aistudio.google.com/apikey
- 앱은 `api-test/.env` → `image-understanding/.env` → 현재폴더 `.env` 순으로 키를 찾습니다.

## 3. 실행

VSCode 터미널(자동으로 .venv 활성화됨)에서:

```powershell
python prototypes/image-understanding/app.py
```

출력되는 http://127.0.0.1:7860 주소를 브라우저에서 엽니다.
샘플 이미지: `prototypes/image-understanding/_samples/bengaluru.jpg`

## 4. 다음 개발 방향 (라벨링 고도화)

현재는 Gemini가 바운딩 박스 좌표만 추정합니다. 여기서 발전시킬 부분:

- **정밀 분할**: YOLOe/SAM2를 붙여 박스 → 마스크(픽셀 단위) 라벨로 확장
- **라벨 내보내기**: 결과를 COCO/YOLO/Pascal VOC 형식으로 저장 (재학습용 데이터셋)
- **수동 보정 UI**: 모델이 그린 박스를 사용자가 끌어서 수정하는 기능
- **배치 처리**: 폴더 단위 일괄 라벨링 + 결과 일괄 저장
- **신뢰도/필터**: confidence 임계값, 클래스별 색상/통계

> 바이브 코딩 원칙: 시연 가능한 최소 결과물부터. MOCK으로 흐름을 먼저 잡고 실제 모델은 나중에.
