"""프로젝트(노트북) + 데이터 검수 워크플로 저장소 — SQLite.

NotebookLM 처럼 작업을 '프로젝트(노트북)' 단위로 나눈다. 각 프로젝트는 소스
(이미지셋·문서·공공데이터·보고서)를 담고, 소스마다 검수 상태(대기/승인/반려)와
검수자·검수시각을 관리한다.

    projects(id, name, emoji, created)
    sources(id, project_id, name, kind, review, reviewer, reviewed_at)
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "storage" / "projects.db"
_lock = threading.Lock()

REVIEW_STATES = ("대기", "승인", "반려")


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS projects "
        "(id TEXT PRIMARY KEY, name TEXT NOT NULL, emoji TEXT, created REAL NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sources ("
        "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, name TEXT NOT NULL, "
        "kind TEXT, review TEXT NOT NULL DEFAULT '대기', reviewer TEXT, reviewed_at REAL)"
    )


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


# ── 시드(데모) ───────────────────────────────────────────────────────
_SEED = [
    (
        "🛣️",
        "도로 파손 라벨링",
        [
            ("road_2026Q2 이미지셋 (18,706장)", "이미지셋", "승인"),
            ("포트홀_보수_기준.md", "문서", "승인"),
            ("도로파손_탐지로그_2026Q2.csv", "공공데이터", "대기"),
        ],
    ),
    (
        "🏗️",
        "시설물 안전점검",
        [
            ("시설물_점검_주기.md", "문서", "승인"),
            ("교량 점검 이미지셋 (2,140장)", "이미지셋", "반려"),
            ("시설물 안전등급 현황", "공공데이터", "대기"),
        ],
    ),
]


def ensure_seeded() -> None:
    with _lock, _connect() as conn:
        _init(conn)
        if conn.execute("SELECT 1 FROM projects LIMIT 1").fetchone():
            return
        now = time.time()
        for i, (emoji, name, sources) in enumerate(_SEED):
            pid = _new_id()
            conn.execute(
                "INSERT INTO projects(id, name, emoji, created) VALUES (?,?,?,?)",
                (pid, name, emoji, now - i * 86400),
            )
            for sname, kind, review in sources:
                reviewer = "박도현" if review != "대기" else None
                rat = now - i * 3600 if review != "대기" else None
                conn.execute(
                    "INSERT INTO sources(id, project_id, name, kind, review, reviewer, reviewed_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (_new_id(), pid, sname, kind, review, reviewer, rat),
                )


# ── 조회/변경 ────────────────────────────────────────────────────────
def _project_summary(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    srcs = conn.execute("SELECT review FROM sources WHERE project_id = ?", (row["id"],)).fetchall()
    total = len(srcs)
    approved = sum(1 for s in srcs if s["review"] == "승인")
    pending = sum(1 for s in srcs if s["review"] == "대기")
    return {
        "id": row["id"],
        "name": row["name"],
        "emoji": row["emoji"] or "📁",
        "created": row["created"],
        "source_count": total,
        "approved": approved,
        "pending": pending,
        "progress": round(100 * approved / total) if total else 0,
    }


def list_projects() -> dict:
    ensure_seeded()
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created DESC").fetchall()
        return {"projects": [_project_summary(conn, r) for r in rows]}


def get_project(pid: str) -> dict | None:
    ensure_seeded()
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
        if not row:
            return None
        srcs = conn.execute(
            "SELECT * FROM sources WHERE project_id = ? ORDER BY rowid", (pid,)
        ).fetchall()
        data = _project_summary(conn, row)
        data["sources"] = [
            {
                "id": s["id"],
                "name": s["name"],
                "kind": s["kind"] or "문서",
                "review": s["review"],
                "reviewer": s["reviewer"] or "",
                "reviewed_at": s["reviewed_at"] or 0,
            }
            for s in srcs
        ]
        return data


def create_project(name: str, emoji: str = "📁") -> dict:
    ensure_seeded()
    pid = _new_id()
    with _lock, _connect() as conn:
        _init(conn)
        conn.execute(
            "INSERT INTO projects(id, name, emoji, created) VALUES (?,?,?,?)",
            (pid, (name or "새 프로젝트").strip(), (emoji or "📁").strip(), time.time()),
        )
    return get_project(pid) or {}


def add_source(pid: str, name: str, kind: str = "문서") -> dict | None:
    with _lock, _connect() as conn:
        _init(conn)
        if not conn.execute("SELECT 1 FROM projects WHERE id = ?", (pid,)).fetchone():
            return None
        conn.execute(
            "INSERT INTO sources(id, project_id, name, kind, review) VALUES (?,?,?,?,'대기')",
            (_new_id(), pid, (name or "새 소스").strip(), (kind or "문서").strip()),
        )
    return get_project(pid)


def set_review(source_id: str, status: str, reviewer: str = "") -> dict | None:
    """소스 검수 상태 변경(대기/승인/반려) + 검수자·시각 기록. 프로젝트 상세 반환."""
    if status not in REVIEW_STATES:
        return None
    with _lock, _connect() as conn:
        _init(conn)
        row = conn.execute("SELECT project_id FROM sources WHERE id = ?", (source_id,)).fetchone()
        if not row:
            return None
        if status == "대기":
            conn.execute(
                "UPDATE sources SET review=?, reviewer=NULL, reviewed_at=NULL WHERE id=?",
                (status, source_id),
            )
        else:
            conn.execute(
                "UPDATE sources SET review=?, reviewer=?, reviewed_at=? WHERE id=?",
                (status, (reviewer or "검수자").strip(), time.time(), source_id),
            )
        pid = row["project_id"]
    return get_project(pid)


def delete_project(pid: str) -> dict:
    with _lock, _connect() as conn:
        _init(conn)
        conn.execute("DELETE FROM sources WHERE project_id = ?", (pid,))
        conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
    return {"deleted": pid}
