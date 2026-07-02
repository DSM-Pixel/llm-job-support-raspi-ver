#!/usr/bin/env bash
# 통합 웹 플랫폼(FastAPI) 로컬 실행 — macOS/Linux/Git Bash
# 사용법:  ./run_web.sh           (기본 127.0.0.1:8000)
#          PORT=9000 ./run_web.sh

set -euo pipefail

PORT="${PORT:-8000}"
BIND_HOST="${HOST:-127.0.0.1}"

if [ -x ".venv/Scripts/python" ]; then
    PYTHON=".venv/Scripts/python"   # Windows venv 레이아웃
elif [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"       # POSIX venv 레이아웃
else
    echo "[!] .venv 가 없습니다. 먼저 'uv sync --extra web' 를 실행하세요." >&2
    exit 1
fi

echo "GNSoft AI 플랫폼 → http://${BIND_HOST}:${PORT}"
exec "$PYTHON" -m uvicorn backend.app:app --host "$BIND_HOST" --port "$PORT" --reload
