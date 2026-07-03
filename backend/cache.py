"""경량 캐시 계층 — Redis 우선, 없으면 인메모리 폴백.

REDIS_URL 환경변수가 있고 redis 패키지가 설치돼 있으면 Redis 를, 아니면
프로세스 인메모리 dict(만료 포함)를 쓴다. 덕분에 로컬 개발(Redis 없음)에서도
코드 수정 없이 동작하고, 배포 시 REDIS_URL 만 주입하면 다중 인스턴스가
공유하는 캐시가 된다.

    import cache
    cache.set_json("k", {...}, ttl=60)
    cache.get_json("k")   # dict 또는 None
    cache.delete("k")     # 무효화
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
import time

_TTL_DEFAULT = 60

_redis = None
_BACKEND = "memory"

# 인메모리 폴백 저장소: key -> (expire_epoch, json_str)
_mem: dict[str, tuple[float, str]] = {}
_mem_lock = threading.Lock()


def _init_redis() -> None:
    """REDIS_URL 이 있으면 연결을 시도한다. 실패하면 조용히 인메모리로 폴백."""
    global _redis, _BACKEND
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return
    try:
        import redis  # 선택 의존성(pyproject web extras). 없으면 ImportError → 폴백.

        client = redis.Redis.from_url(url, decode_responses=True, socket_timeout=1)
        client.ping()
        _redis = client
        _BACKEND = "redis"
        print(f"[cache] Redis 연결됨: {url}")
    except Exception as exc:
        print(f"[cache] Redis 사용 불가 — 인메모리 폴백: {exc}")
        _redis = None


_init_redis()


def backend_name() -> str:
    """현재 캐시 백엔드('redis' 또는 'memory') — 상태 표시·헬스체크용."""
    return _BACKEND


def get_json(key: str):
    """캐시에서 JSON 값을 읽는다. 없거나 만료면 None."""
    if _redis is not None:
        try:
            raw = _redis.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None
    with _mem_lock:
        item = _mem.get(key)
        if not item:
            return None
        expire, raw = item
        if expire < time.time():
            _mem.pop(key, None)
            return None
        return json.loads(raw)


def set_json(key: str, value, ttl: int = _TTL_DEFAULT) -> None:
    """JSON 직렬화 가능한 값을 ttl(초) 동안 캐시한다."""
    raw = json.dumps(value, ensure_ascii=False)
    if _redis is not None:
        with contextlib.suppress(Exception):
            _redis.set(key, raw, ex=ttl)
        return
    with _mem_lock:
        _mem[key] = (time.time() + ttl, raw)


def delete(key: str) -> None:
    """캐시 키를 무효화한다(활동 기록 시 해당 통계 캐시 삭제용)."""
    if _redis is not None:
        with contextlib.suppress(Exception):
            _redis.delete(key)
        return
    with _mem_lock:
        _mem.pop(key, None)
