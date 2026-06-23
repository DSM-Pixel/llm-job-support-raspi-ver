"""GNSoft AI 플랫폼 통합 FastAPI 앱.

실행:
    uv pip install -e ".[web]"      # 또는: pip install fastapi "uvicorn[standard]"
    uvicorn backend.app:app --reload
    → http://localhost:8000  (web/ UI + /api)

구조:
    - /api/*           : 업무 엔드포인트 (현재 services.py 의 MOCK 사용)
    - /                : web/ 정적 프론트엔드 (index.html → pages/dashboard.html)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import services, yolo_service

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="GNSoft AI 플랫폼", version="0.1.0")


# ── 요청 스키마 ──────────────────────────────────────────────────────
class QueryIn(BaseModel):
    question: str


class RagSearchIn(BaseModel):
    query: str
    top_k: int = 4


class RagIndexIn(BaseModel):
    docs: list[dict] = []
    sources: list[str] = []
    use_samples: bool = True


class DetectIn(BaseModel):
    preset: str = "도로 파손/포트홀 찾기"
    custom_prompt: str = ""
    min_conf: int = 0
    image_name: str = ""


class ReportIn(BaseModel):
    report_type: str = "현황 분석"
    period: str = "최근 3년"
    sources: list[str] = []


class UploadIn(BaseModel):
    name: str = ""


class WebSearchIn(BaseModel):
    keyword: str = ""


class SaveLabelsIn(BaseModel):
    image_name: str = ""
    label_count: int = 0


# ── API 라우트 ───────────────────────────────────────────────────────
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "backend": services.BACKEND}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return services.dashboard_stats()


@app.post("/api/query")
def query(body: QueryIn) -> dict:
    return services.route_query(body.question)


@app.post("/api/rag/search")
def rag_search(body: RagSearchIn) -> dict:
    return services.rag_search(body.query, body.top_k)


@app.post("/api/rag/index")
def rag_index(body: RagIndexIn) -> dict:
    return services.rag_index(body.docs, body.sources, body.use_samples)


@app.post("/api/rag/web-search")
def rag_web_search(body: WebSearchIn) -> dict:
    return services.rag_web_search(body.keyword)


@app.post("/api/rag/reset")
def rag_reset() -> dict:
    return services.rag_reset()


@app.get("/api/rag/doc")
def rag_doc(source: str) -> dict:
    return services.rag_get_doc(source)


@app.post("/api/labeling/detect")
def labeling_detect(body: DetectIn) -> dict:
    return services.labeling_detect(body.preset, body.custom_prompt, body.min_conf, body.image_name)


@app.post("/api/labeling/detect-image")
async def labeling_detect_image(image: UploadFile = File(...)) -> dict:
    """업로드 이미지에서 실제 YOLO(best.pt)로 박스 탐지. 모델 없으면 MOCK."""
    data = await image.read()
    return yolo_service.detect_boxes(data)


@app.post("/api/labeling/analyze-image")
async def labeling_analyze_image(
    image: UploadFile = File(...),
    preset: str = Form("도로 파손/포트홀 찾기"),
    custom_prompt: str = Form(""),
) -> dict:
    """업로드 이미지를 실제 Gemini Vision으로 설명 분석. 키 없으면 MOCK."""
    data = await image.read()
    return services.analyze_image_vision(
        data, preset, custom_prompt, image.content_type or "image/png"
    )


@app.get("/api/labeling/model")
def labeling_model() -> dict:
    """탐지 모델 사용 가능 여부."""
    return {"yolo_available": yolo_service.model_available()}


@app.post("/api/labeling/save")
def labeling_save(body: SaveLabelsIn) -> dict:
    return services.save_labeling(body.image_name, body.label_count)


@app.post("/api/report")
def report(body: ReportIn) -> dict:
    return services.generate_report(body.report_type, body.period, body.sources)


@app.get("/api/datasets")
def datasets() -> dict:
    return services.list_datasets()


@app.post("/api/datasets/upload")
def datasets_upload(body: UploadIn) -> dict:
    return services.upload_dataset(body.name)


# ── 정적 프론트엔드 (반드시 API 라우트 등록 이후에 마운트) ──────────────
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
