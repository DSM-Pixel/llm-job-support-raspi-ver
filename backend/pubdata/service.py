"""공공데이터 연계 조회 — 키워드 → 도메인 → 통계 시리즈 + 관련 데이터셋.

store(통합 저장소)만 조회하므로, 데이터셋을 늘려도(레지스트리 추가) 여기 코드는
그대로다. 자연어 요약은 services 계층(Gemini)에 맡긴다.
"""

from __future__ import annotations

from urllib.parse import quote

from . import adapters, ingest, registry, store


def _portal_url(query: str) -> str:
    return f"https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword={quote(query)}"


def _dataset_card(d: dict) -> dict:
    return {
        "id": d["id"],
        "title": d["name"],
        "provider": d["provider"],
        "category": d["category"],
        "format": d["fmt"],
        "url": _portal_url(d["name"]),
    }


def build(keyword: str) -> dict:
    """도메인 통계 + 관련 데이터셋 묶음을 만든다(요약 제외)."""
    ingest.ensure_seeded()
    kw = (keyword or "").strip() or "도로 파손"
    domain = registry.match_domain(kw)
    domain_sets = registry.datasets_for(domain)
    primary = domain_sets[0]

    s = store.series(primary["id"])
    primary_live = store.source_mode(primary["id"]) == "LIVE"
    stats = {
        "title": primary["chart_title"],
        "unit": s["unit"] or primary["unit"],
        "labels": s["labels"],
        "values": s["values"],
        "sample": not primary_live,  # 시드면 True(샘플), 실데이터면 False
        "dataset": primary["name"],
    }
    insights = [d["insight"] for d in domain_sets if d.get("insight")][:3]
    return {
        "keyword": kw,
        "domain": domain,
        "datasets": [_dataset_card(d) for d in domain_sets],
        "stats": stats,
        "insights": insights,
        "portal_url": _portal_url(kw),
        "live": primary_live,  # 이 도메인 대표 데이터셋이 실데이터인지
        "key_registered": adapters.has_key(),  # 서비스키 등록 여부(참고)
        "dataset_total": len(registry.DATASETS),  # 등록된 전체 데이터셋 수
        "dataset_matched": len(domain_sets),
    }


def catalog() -> dict:
    """등록된 전체 데이터셋 카탈로그(데이터 관리·현황용)."""
    ingest.ensure_seeded()
    return {
        "total": len(registry.DATASETS),
        "loaded": store.count_datasets(),
        "live": adapters.has_key(),
        "datasets": [
            {
                "id": d["id"],
                "domain": d["domain"],
                "name": d["name"],
                "provider": d["provider"],
                "dim": d["dim"],
                "live_ready": bool(d.get("live") and d["live"].get("endpoint")),
                "loaded": store.source_mode(d["id"]),  # 'LIVE' | 'SEED'
            }
            for d in registry.DATASETS
        ],
    }
