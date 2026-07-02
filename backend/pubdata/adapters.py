"""어댑터 — 제각각인 공공데이터 응답을 공통 스키마로 변환.

핵심: 데이터셋마다 응답 컬럼명이 다르므로, registry 의 live.mapping 으로
(기간/지역=dim, 값=value) 컬럼을 지정해 공통 형태 {dim_key, value} 로 맞춘다.

실 API 호출은 DATA_GO_KR_KEY 가 있고 live 설정이 있을 때만. 그 외에는 None 을
반환해 ingest 가 시드로 폴백하게 한다.
"""

from __future__ import annotations

import csv
import io
import os
import re
from typing import Any

import requests

# 브라우저형 UA — 일부 파일 서버가 기본 요청을 403 으로 막는 경우 완화.
_UA = "Mozilla/5.0 (compatible; GNSoftPubData/0.1)"


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


def _transform_dim(value: str, kind: str | None) -> str | None:
    """dim 키 변환. 'month'=날짜에서 월 추출, 'sigungu'=주소에서 시군구 추출."""
    if not kind:
        return value
    if kind == "month":
        m = re.search(r"\d{4}[-/.]?(\d{2})", value)  # 2026-03-01 → '3'
        return str(int(m.group(1))) if m else None
    if kind == "sigungu":
        # '서울특별시 강남구 …' → '강남구' (상위 특별시/광역시/도는 건너뛰고 하위 시군구)
        parts = [p for p in value.split() if p and p[-1] in "시군구"]
        if not parts:
            return value
        top = parts[0]
        if len(parts) >= 2 and (top.endswith(("특별시", "광역시")) or top.endswith("도")):
            return parts[1]
        return top
    return value


def to_common(dataset: dict, raw_rows: list[dict]) -> list[dict]:
    """실 API/CSV 원시 행 목록 → 공통 스키마 관측치 목록.

    live.mapping = {"dim": "<dim 컬럼>", "value": "<값 컬럼>", "dim_transform": "month|sigungu"}
    live.aggregate == "sum" 이면 같은 dim_key 를 합산한다(지점·일 단위 → 지역·월 단위).
    """
    live = dataset.get("live") or {}
    mapping = live.get("mapping") or {}
    dim_col = mapping.get("dim")
    val_col = mapping.get("value")
    transform = mapping.get("dim_transform")
    if not (dim_col and val_col):
        return []

    pairs: list[tuple[str, float]] = []
    for row in raw_rows:
        dim_raw = _dig(row, dim_col)
        value = _dig(row, val_col)
        if dim_raw is None or value is None:
            continue
        dim_key = _transform_dim(str(dim_raw), transform)
        if dim_key is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        pairs.append((dim_key, value))

    if live.get("aggregate") == "sum":  # 같은 지역/기간 키끼리 합산(첫 등장 순서 유지)
        agg: dict[str, float] = {}
        order: list[str] = []
        for key, value in pairs:
            if key not in agg:
                order.append(key)
            agg[key] = agg.get(key, 0.0) + value
        pairs = [(key, agg[key]) for key in order]

    return [
        {
            "dataset_id": dataset["id"],
            "domain": dataset["domain"],
            "dim_type": dataset["dim"],
            "dim_key": key,
            "ordinal": i,
            "value": value,
            "unit": dataset["unit"],
            "source": dataset["name"],
        }
        for i, (key, value) in enumerate(pairs)
    ]


def _fetch_json(dataset: dict, live: dict, timeout: int) -> list[dict] | None:
    """JSON REST 오픈API(apis.data.go.kr) 호출 → 공통 스키마. 서비스키 필요."""
    key = _service_key()
    if not key:
        return None
    params = {"serviceKey": key, **(live.get("params") or {})}
    try:
        resp = requests.get(
            live["endpoint"], params=params, timeout=timeout, headers={"User-Agent": _UA}
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None
    rows: Any = payload  # rows_path(예: 'response.body.items.item')로 항목 배열 진입
    for part in (live.get("rows_path") or "").split("."):
        if part and isinstance(rows, dict):
            rows = rows.get(part)
    if not isinstance(rows, list):
        return None
    return to_common(dataset, rows)


def _fetch_csv(dataset: dict, live: dict, timeout: int) -> list[dict] | None:
    """CSV 파일데이터 다운로드 → 공통 스키마. 서비스키 없이도 시도(공개 파일)."""
    try:
        resp = requests.get(live["endpoint"], timeout=timeout, headers={"User-Agent": _UA})
        resp.raise_for_status()
        resp.encoding = live.get("encoding") or resp.apparent_encoding or "utf-8"
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
    except Exception:
        return None
    return to_common(dataset, rows) or None


def fetch_live(dataset: dict, timeout: int = 8) -> list[dict] | None:
    """실 데이터 수집 → 공통 스키마. 설정/키 없거나 실패하면 None(→ 시드 폴백).

    live.type: "json"(기본, 오픈API) 또는 "csv"(파일데이터). endpoint 필수.
    """
    live = dataset.get("live")
    if not (live and live.get("endpoint")):
        return None
    if live.get("type") == "csv":
        return _fetch_csv(dataset, live, timeout)
    return _fetch_json(dataset, live, timeout)


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
