"""수집(ingest) — 각 데이터셋을 store 에 적재.

데이터셋별로 실 API(fetch_live)를 먼저 시도하고, 키/설정이 없거나 실패하면
시드(from_seed)로 폴백한다. 결과를 store.replace_dataset 으로 통째 교체.
"""

from __future__ import annotations

from . import adapters, registry, store


def ingest_one(dataset: dict) -> dict:
    """데이터셋 하나 적재. {id, rows, source} 반환."""
    rows = adapters.fetch_live(dataset)
    source = "LIVE"
    if not rows:  # 키 없음/실패/빈 응답 → 시드
        rows = adapters.from_seed(dataset)
        source = "SEED"
    store.replace_dataset(dataset["id"], rows, source)
    return {"id": dataset["id"], "rows": len(rows), "source": source}


def ingest_all() -> list[dict]:
    store.init()
    return [ingest_one(d) for d in registry.DATASETS]


def ensure_seeded() -> None:
    """저장소가 비어 있으면 최초 1회 적재. (서버 부팅 시 지연 호출)"""
    store.init()
    if store.is_empty():
        ingest_all()
