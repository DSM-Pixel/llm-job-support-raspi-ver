# prototypes — 기능별 원형 데모

각 기능을 독립적으로 검증한 Gradio/스크립트 데모 모음입니다.
지금은 이 기능들이 통합 웹 플랫폼(`web/` + `backend/`)으로 합쳐졌고,
여기 코드는 **실험·참고용 원형**으로 보존합니다.

| 폴더 | 기능 | 통합 위치 |
|------|------|-----------|
| `api-test` | Gemini/Claude API 연결 테스트 | `backend/services.py` |
| `image-understanding` | YOLO 도로파손 탐지 + 라벨링 + SAM 분할 | `backend/yolo_service.py`, `web` 라벨링 |
| `rag-search` | Hybrid RAG 검색 | `backend/services.py`, `web` RAG |

> 새 기능은 가급적 통합 서버 쪽에 붙이고, 빠른 단독 실험이 필요할 때만 이 폴더를 쓰세요.
