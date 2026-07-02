"""SQLite 통합 저장소.

모든 데이터셋을 하나의 긴(long) 테이블에 공통 스키마로 쌓는다.
    observations(dataset_id, domain, dim_type, dim_key, ordinal, value, unit, source)

이렇게 통합해 두면 데이터셋이 몇 개든 화면·통계·보고서는 이 한 곳만 조회하면 되고,
데이터셋끼리 비교·조인도 가능해진다.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "storage" / "pubdata.db"
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                dataset_id TEXT NOT NULL,
                domain     TEXT NOT NULL,
                dim_type   TEXT NOT NULL,   -- 'period' | 'region'
                dim_key    TEXT NOT NULL,   -- 예: '3'(월), '서울'
                ordinal    INTEGER NOT NULL, -- 정렬 순서
                value      REAL NOT NULL,
                unit       TEXT,
                source     TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_dataset ON observations(dataset_id)")
        # 데이터셋별 적재 출처('LIVE'=실데이터 / 'SEED'=시드) — stats.sample 판정용.
        conn.execute(
            "CREATE TABLE IF NOT EXISTS dataset_source "
            "(dataset_id TEXT PRIMARY KEY, mode TEXT NOT NULL)"
        )


def replace_dataset(dataset_id: str, rows: list[dict], mode: str = "SEED") -> int:
    """한 데이터셋의 관측치를 통째로 교체(재수집 시 중복 방지) + 적재 출처 기록."""
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM observations WHERE dataset_id = ?", (dataset_id,))
        conn.executemany(
            """INSERT INTO observations
               (dataset_id, domain, dim_type, dim_key, ordinal, value, unit, source)
               VALUES (:dataset_id, :domain, :dim_type, :dim_key, :ordinal, :value, :unit, :source)""",
            rows,
        )
        conn.execute(
            "INSERT INTO dataset_source(dataset_id, mode) VALUES (?, ?) "
            "ON CONFLICT(dataset_id) DO UPDATE SET mode = excluded.mode",
            (dataset_id, mode),
        )
        return len(rows)


def source_mode(dataset_id: str) -> str:
    """데이터셋 적재 출처('LIVE'|'SEED'). 없으면 'SEED'."""
    with _lock, _connect() as conn:
        cur = conn.execute("SELECT mode FROM dataset_source WHERE dataset_id = ?", (dataset_id,))
        row = cur.fetchone()
    return row["mode"] if row else "SEED"


def series(dataset_id: str) -> dict:
    """데이터셋의 통계 시리즈를 차트용으로 반환: {labels, values, unit}."""
    with _lock, _connect() as conn:
        cur = conn.execute(
            "SELECT dim_key, value, unit FROM observations WHERE dataset_id = ? ORDER BY ordinal",
            (dataset_id,),
        )
        rows = cur.fetchall()
    return {
        "labels": [r["dim_key"] for r in rows],
        "values": [r["value"] for r in rows],
        "unit": rows[0]["unit"] if rows else "",
    }


def count_datasets() -> int:
    with _lock, _connect() as conn:
        cur = conn.execute("SELECT COUNT(DISTINCT dataset_id) AS n FROM observations")
        return int(cur.fetchone()["n"])


def is_empty() -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("SELECT 1 FROM observations LIMIT 1")
        return cur.fetchone() is None
