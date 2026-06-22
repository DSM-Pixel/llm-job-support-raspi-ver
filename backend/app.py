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

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import services

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="GNSoft AI 플랫폼", version="0.1.0")


# ── 요청 스키마 ──────────────────────────────────────────────────────
class QueryIn(BaseModel):
    question: str


class RagSearchIn(BaseModel):
    query: str
    top_k: int = 4


class RagIndexIn(BaseModel):
    sources: list[str] = []
    use_samples: bool = True


class DetectIn(BaseModel):
    preset: str = "도로 파손/포트홀 찾기"
    custom_prompt: str = ""
    min_conf: int = 0


class ReportIn(BaseModel):
    report_type: str = "현황 분석"
    period: str = "최근 3년"
    sources: list[str] = []


class UploadIn(BaseModel):
    name: str = ""


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
    return services.rag_index(body.sources, body.use_samples)


@app.post("/api/labeling/detect")
def labeling_detect(body: DetectIn) -> dict:
    return services.labeling_detect(body.preset, body.custom_prompt, body.min_conf)


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
