"""어댑터 — 제각각인 공공데이터 응답을 공통 스키마로 변환.

핵심: 데이터셋마다 응답 컬럼명이 다르므로, registry 의 live.mapping 으로
(기간/지역=dim, 값=value) 컬럼을 지정해 공통 형태 {dim_key, value} 로 맞춘다.

실 API 호출은 DATA_GO_KR_KEY 가 있고 live 설정이 있을 때만. 그 외에는 None 을
반환해 ingest 가 시드로 폴백하게 한다.
"""

from __future__ import annotations

import os
from typing import Any

import requests


def _service_key() -> str | None:
    """공공데이터포털 서비스키. services._data_go_kr_key 와 동일 소스."""
    from pathlib import Path

    env = Path(__file__).resolve().parents[2] / "prototypes" / "api-test" / ".env"
    try:
        for line in env.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            if k.strip() == "DATA_GO_KR_KEY":
                val = v.strip().strip('"').strip("'")
                if val:
                    return val
    except OSError:
        pass
    return os.getenv("DATA_GO_KR_KEY")


def has_key() -> bool:
    return bool(_service_key())


def _dig(row: dict, path: str) -> Any:
    """'a.b' 형태 경로로 중첩 dict 값을 꺼낸다."""
    cur: Any = row
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def to_common(dataset: dict, raw_rows: list[dict]) -> list[dict]:
    """실 API 원시 행 목록 → 공통 스키마 관측치 목록.

    live.mapping = {"dim": "<응답 dim 컬럼>", "value": "<응답 값 컬럼>"} 를 사용.
    """
    mapping = (dataset.get("live") or {}).get("mapping") or {}
    dim_col = mapping.get("dim")
    val_col = mapping.get("value")
    out: list[dict] = []
    if not (dim_col and val_col):
        return out
    for i, row in enumerate(raw_rows):
        dim_key = _dig(row, dim_col)
        value = _dig(row, val_col)
        if dim_key is None or value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "dataset_id": dataset["id"],
                "domain": dataset["domain"],
                "dim_type": dataset["dim"],
                "dim_key": str(dim_key),
                "ordinal": i,
                "value": value,
                "unit": dataset["unit"],
                "source": dataset["name"],
            }
        )
    return out


def fetch_live(dataset: dict, timeout: int = 8) -> list[dict] | None:
    """실 API 호출 → 공통 스키마. 키/설정 없거나 실패하면 None(→ 시드 폴백)."""
    live = dataset.get("live")
    key = _service_key()
    if not (live and live.get("endpoint") and key):
        return None
    params = {"serviceKey": key, **(live.get("params") or {})}
    try:
        resp = requests.get(live["endpoint"], params=params, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None
    # 응답에서 행 목록 위치(live.rows_path, 예: 'response.body.items') 추출.
    rows: Any = payload
    for part in (live.get("rows_path") or "").split("."):
        if part and isinstance(rows, dict):
            rows = rows.get(part)
    if not isinstance(rows, list):
        return None
    return to_common(dataset, rows)


def from_seed(dataset: dict) -> list[dict]:
    """시드(시연/폴백) → 공통 스키마."""
    return [
        {
            "dataset_id": dataset["id"],
            "domain": dataset["domain"],
            "dim_type": dataset["dim"],
            "dim_key": str(k),
            "ordinal": i,
            "value": float(v),
            "unit": dataset["unit"],
            "source": dataset["name"],
        }
        for i, (k, v) in enumerate(dataset["seed"])
    ]
