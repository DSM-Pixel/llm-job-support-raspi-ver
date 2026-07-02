"""로그인·회원가입 — SQLite 사용자·세션 저장소.

- 비밀번호: PBKDF2-HMAC-SHA256(20만회) + 사용자별 salt (stdlib만 사용, 평문 저장 금지).
- 동의(법적 요건): 필수(이용약관·개인정보 수집이용) 동의 '일시'를 기록하고,
  선택(알림 수신)은 여부만 저장한다. 필수 미동의 시 가입 자체를 거부한다.
- 세션: 랜덤 토큰(7일 만료). 프론트는 localStorage 에 보관하고 /api/auth/me 로 검증.

    users(id, email, pw, name, company, team, marketing,
          terms_at, privacy_at, created)
    sessions(token, user_id, expires)
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "storage" / "users.db"
_lock = threading.Lock()

_SESSION_TTL = 7 * 86400  # 7일
_RESET_TTL = 30 * 60  # 비밀번호 재설정 링크 유효시간(30분)
_PBKDF2_ITERS = 200_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw TEXT NOT NULL, "
        "name TEXT NOT NULL, company TEXT, team TEXT, marketing INTEGER DEFAULT 0, "
        "terms_at REAL NOT NULL, privacy_at REAL NOT NULL, created REAL NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reset_tokens ("
        "token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL)"
    )


# ── 비밀번호 해시 ────────────────────────────────────────────────────
def _hash_pw(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERS
    ).hex()
    return f"{salt}${digest}"


def _verify_pw(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_pw(password, salt), stored)


# ── 세션 ─────────────────────────────────────────────────────────────
def _issue_session(conn: sqlite3.Connection, user_id: str) -> str:
    token = secrets.token_hex(24)
    conn.execute(
        "INSERT INTO sessions(token, user_id, expires) VALUES (?,?,?)",
        (token, user_id, time.time() + _SESSION_TTL),
    )
    conn.execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))  # 만료 정리
    return token


def _user_payload(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "company": row["company"] or "",
        "team": row["team"] or "",
        "marketing": bool(row["marketing"]),
    }


# ── 공개 API ─────────────────────────────────────────────────────────
def signup(
    email: str,
    password: str,
    name: str,
    company: str = "",
    team: str = "",
    agree_terms: bool = False,
    agree_privacy: bool = False,
    agree_marketing: bool = False,
) -> dict:
    """회원가입. 필수 동의(약관·개인정보) 없으면 거부. 성공 시 자동 로그인(토큰)."""
    email = (email or "").strip().lower()
    name = (name or "").strip()
    if not _EMAIL_RE.match(email):
        return {"ok": False, "error": "올바른 이메일 주소를 입력해주세요."}
    if len(password or "") < 8:
        return {"ok": False, "error": "비밀번호는 8자 이상이어야 합니다."}
    if not name:
        return {"ok": False, "error": "이름을 입력해주세요."}
    # 법적 요건: 필수 동의 없이는 개인정보를 수집·저장하지 않는다.
    if not (agree_terms and agree_privacy):
        return {
            "ok": False,
            "error": "필수 약관(이용약관·개인정보 수집이용)에 동의해야 가입할 수 있습니다.",
        }

    now = time.time()
    with _lock, _connect() as conn:
        _init(conn)
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            return {"ok": False, "error": "이미 가입된 이메일입니다. 로그인해주세요."}
        uid = secrets.token_hex(8)
        conn.execute(
            "INSERT INTO users(id, email, pw, name, company, team, marketing, "
            "terms_at, privacy_at, created) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                uid,
                email,
                _hash_pw(password),
                name,
                (company or "").strip(),
                (team or "").strip(),
                1 if agree_marketing else 0,
                now,  # 동의 일시 기록(철회·분쟁 대비)
                now,
                now,
            ),
        )
        token = _issue_session(conn, uid)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return {
        "ok": True,
        "token": token,
        "user": _user_payload(row),
        "message": "가입이 완료되었습니다.",
    }


def login(email: str, password: str) -> dict:
    email = (email or "").strip().lower()
    with _lock, _connect() as conn:
        _init(conn)
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        # 데모 플랫폼 — 미가입/비밀번호 오류를 구분해 안내한다.
        if not row:
            return {
                "ok": False,
                "code": "not_registered",
                "error": "가입되지 않은 이메일입니다. 회원가입 후 이용해주세요.",
            }
        if not _verify_pw(password or "", row["pw"]):
            return {"ok": False, "error": "비밀번호가 올바르지 않습니다."}
        token = _issue_session(conn, row["id"])
    return {"ok": True, "token": token, "user": _user_payload(row)}


def me(token: str) -> dict:
    """토큰 검증 — 유효하면 사용자 정보."""
    with _lock, _connect() as conn:
        _init(conn)
        s = conn.execute(
            "SELECT user_id, expires FROM sessions WHERE token = ?", (token or "",)
        ).fetchone()
        if not s or s["expires"] < time.time():
            return {"ok": False, "error": "세션이 만료되었습니다. 다시 로그인해주세요."}
        row = conn.execute("SELECT * FROM users WHERE id = ?", (s["user_id"],)).fetchone()
        if not row:
            return {"ok": False, "error": "사용자를 찾을 수 없습니다."}
    return {"ok": True, "user": _user_payload(row)}


def logout(token: str) -> dict:
    with _lock, _connect() as conn:
        _init(conn)
        conn.execute("DELETE FROM sessions WHERE token = ?", (token or "",))
    return {"ok": True, "message": "로그아웃되었습니다."}


# ── 비밀번호 재설정 ──────────────────────────────────────────────────
def request_reset(email: str) -> dict:
    """재설정 링크 요청. 계정 열거(enumeration) 방지를 위해 가입 여부와 관계없이
    동일한 안내를 돌려준다. 실제 서비스라면 이메일로 링크를 발송한다."""
    email = (email or "").strip().lower()
    generic = {
        "ok": True,
        "message": "가입된 이메일이라면 비밀번호 재설정 링크를 보냈습니다. 메일함을 확인해주세요.",
    }
    if not _EMAIL_RE.match(email):
        return generic

    with _lock, _connect() as conn:
        _init(conn)
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            return generic  # 미가입 — 동일 응답으로 존재 여부를 숨긴다
        token = secrets.token_hex(24)
        conn.execute("DELETE FROM reset_tokens WHERE user_id = ?", (row["id"],))  # 기존 요청 무효화
        conn.execute(
            "INSERT INTO reset_tokens(token, user_id, expires) VALUES (?,?,?)",
            (token, row["id"], time.time() + _RESET_TTL),
        )
        conn.execute("DELETE FROM reset_tokens WHERE expires < ?", (time.time(),))  # 만료 정리

    link = f"/pages/reset.html?token={token}"
    # 데모에는 메일러가 없어 콘솔에 출력하고 dev_link 로 함께 돌려준다.
    # ⚠ 운영 배포 시 dev_link 는 제거할 것 — 응답에 담으면 계정 존재가 노출된다.
    # 로그는 Windows 콘솔(cp1252)에서도 안전하도록 ASCII 로만 남긴다.
    print(f"[password-reset] {email} -> {link}")
    return {**generic, "dev_link": link}


def reset_password(token: str, new_password: str) -> dict:
    """재설정 토큰(1회용)으로 새 비밀번호를 설정한다. 성공 시 기존 세션은 모두 무효화."""
    if len(new_password or "") < 8:
        return {"ok": False, "error": "비밀번호는 8자 이상이어야 합니다."}
    now = time.time()
    with _lock, _connect() as conn:
        _init(conn)
        row = conn.execute(
            "SELECT user_id, expires FROM reset_tokens WHERE token = ?", (token or "",)
        ).fetchone()
        if not row or row["expires"] < now:
            return {"ok": False, "error": "재설정 링크가 만료되었거나 올바르지 않습니다. 다시 요청해주세요."}
        uid = row["user_id"]
        conn.execute("UPDATE users SET pw = ? WHERE id = ?", (_hash_pw(new_password), uid))
        conn.execute("DELETE FROM reset_tokens WHERE token = ?", (token,))  # 1회용
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))  # 보안: 기존 세션 무효화
    return {"ok": True, "message": "비밀번호가 변경되었습니다. 새 비밀번호로 로그인해주세요."}
