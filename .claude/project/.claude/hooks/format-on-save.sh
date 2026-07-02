#!/usr/bin/env bash
# PostToolUse hook: Edit/Write/MultiEdit 가 .py 파일을 수정하면 ruff format + ruff check --fix 적용.
# 기존 .claude/hooks/format_py.py 훅의 로직을 유지·개명한 셸 버전.
# ruff 미설치 / .py 아님 / 파싱 실패 등 어떤 경우에도 사용자 흐름을 막지 않도록 항상 exit 0.

set -u

PAYLOAD="$(cat)"

# hook payload(JSON)에서 file_path 추출 — python3 이 없으면 조용히 통과
FILE_PATH="$(printf '%s' "$PAYLOAD" | python3 -c '
import json, sys
try:
    payload = json.load(sys.stdin)
    ti = payload.get("tool_input") or {}
    print(ti.get("file_path") or ti.get("path") or "")
except Exception:
    pass
' 2>/dev/null)" || exit 0

[ -n "$FILE_PATH" ] || exit 0
case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;
esac
[ -f "$FILE_PATH" ] || exit 0

command -v ruff >/dev/null 2>&1 || exit 0

ruff format "$FILE_PATH" >/dev/null 2>&1
# 남은 경고만 stderr 로 흘려 Claude 가 확인할 수 있게 한다.
LEFTOVER="$(ruff check --fix --exit-zero "$FILE_PATH" 2>/dev/null)"
if [ -n "$LEFTOVER" ] && ! printf '%s' "$LEFTOVER" | grep -q "All checks passed"; then
  echo "[ruff] $LEFTOVER" >&2
fi

exit 0
