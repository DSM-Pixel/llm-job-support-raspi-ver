#!/usr/bin/env python3
"""의존성 0 MCP 메모리 서버 (stdio, JSON-RPC 2.0).

SQLite에 사실/결정/진행상황을 저장하고 키워드로 검색한다.
컨텍스트에 자동 로드되지 않으므로 평소 토큰 비용은 0이고,
Claude가 memory_search 도구를 호출할 때만 내용을 꺼내온다.

stdout은 JSON-RPC 전용. 로그는 모두 stderr로 보낸다.
"""

import sys
import os
import json
import sqlite3
import datetime

# 한글 입출력 안전: stdio를 UTF-8로 고정
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.environ.get("MEMORY_DB_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory.db"
)
PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "memory", "version": "0.1.0"}


def log(msg: str) -> None:
    print(f"[memory] {msg}", file=sys.stderr, flush=True)


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )"""
    )
    return conn


def _fmt(row) -> str:
    id_, content, tags, created = row
    tagstr = f" [{tags}]" if tags else ""
    return f"#{id_} ({created}){tagstr}\n{content}"


# --- 도구 구현 -------------------------------------------------------------

def t_save(args: dict) -> str:
    content = (args.get("content") or "").strip()
    if not content:
        return "content가 비어있습니다."
    tags = (args.get("tags") or "").strip()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO memories(content, tags, created_at) VALUES(?,?,?)",
            (content, tags, now),
        )
        return f"저장 완료 (id={cur.lastrowid})"


def t_search(args: dict) -> str:
    query = (args.get("query") or "").strip()
    limit = int(args.get("limit") or 5)
    if not query:
        return "query가 비어있습니다."
    terms = query.split()
    where = " AND ".join(["(content LIKE ? OR tags LIKE ?)"] * len(terms))
    params: list = []
    for term in terms:
        like = f"%{term}%"
        params.extend([like, like])
    params.append(limit)
    with db() as conn:
        rows = conn.execute(
            f"SELECT id, content, tags, created_at FROM memories WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
    if not rows:
        return f"'{query}'에 해당하는 메모리 없음."
    return "\n\n".join(_fmt(r) for r in rows)


def t_recent(args: dict) -> str:
    limit = int(args.get("limit") or 10)
    with db() as conn:
        rows = conn.execute(
            "SELECT id, content, tags, created_at FROM memories "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    if not rows:
        return "저장된 메모리 없음."
    return "\n\n".join(_fmt(r) for r in rows)


def t_delete(args: dict) -> str:
    mem_id = args.get("id")
    with db() as conn:
        cur = conn.execute("DELETE FROM memories WHERE id=?", (mem_id,))
        if cur.rowcount == 0:
            return f"id={mem_id} 없음."
        return f"삭제 완료 (id={mem_id})"


TOOLS = [
    {
        "name": "memory_save",
        "description": "사실·결정·진행상황을 장기 메모리에 저장한다. 세션이 바뀌어도 검색으로 다시 꺼낼 수 있다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "저장할 내용"},
                "tags": {"type": "string", "description": "공백으로 구분한 태그 (선택)"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "memory_search",
        "description": "키워드로 저장된 메모리를 검색한다. 여러 단어는 AND로 묶인다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색어 (공백 구분)"},
                "limit": {"type": "integer", "description": "최대 결과 수", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_recent",
        "description": "최근 저장된 메모리를 시간 역순으로 가져온다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "최대 결과 수", "default": 10},
            },
        },
    },
    {
        "name": "memory_delete",
        "description": "id로 메모리 한 건을 삭제한다.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "삭제할 메모리 id"}},
            "required": ["id"],
        },
    },
]

HANDLERS = {
    "memory_save": t_save,
    "memory_search": t_search,
    "memory_recent": t_recent,
    "memory_delete": t_delete,
}


# --- JSON-RPC 루프 ---------------------------------------------------------

def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(msg: dict):
    method = msg.get("method")
    mid = msg.get("id")

    if method == "initialize":
        client_proto = (msg.get("params") or {}).get("protocolVersion", PROTOCOL_VERSION)
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": client_proto,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        handler = HANDLERS.get(name)
        if not handler:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"unknown tool {name}"}}
        try:
            text = handler(args)
        except Exception as e:  # 사용자에게 의미 있는 오류 반환
            log(f"tool error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {"content": [{"type": "text", "text": f"오류: {e}"}], "isError": True},
            }
        return {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text}]}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}

    # notifications/initialized 등 id 없는 알림은 응답하지 않는다
    if mid is None:
        return None
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"unknown method {method}"}}


def main() -> None:
    log(f"starting, db={DB_PATH}")
    db().close()  # 테이블 보장
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp is not None:
            send(resp)


if __name__ == "__main__":
    main()
