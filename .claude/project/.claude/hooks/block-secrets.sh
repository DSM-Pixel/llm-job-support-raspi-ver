#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash): 위험 명령·시크릿 유출 명령을 실행 전에 차단한다.
# 차단 시 exit 2 + stderr 사유 → Claude 가 이유를 보고 다른 방법을 찾는다.
# 판단 불가/파싱 실패 시에는 절대 막지 않는다 (exit 0).

set -u

PAYLOAD="$(cat)"

CMD="$(printf '%s' "$PAYLOAD" | python3 -c '
import json, sys
try:
    payload = json.load(sys.stdin)
    print((payload.get("tool_input") or {}).get("command") or "")
except Exception:
    pass
' 2>/dev/null)" || exit 0

[ -n "$CMD" ] || exit 0

block() {
  echo "[block-secrets] 차단됨: $1" >&2
  echo "[block-secrets] 명령: $CMD" >&2
  exit 2
}

# ── 파괴적 명령 ──────────────────────────────────────────────
echo "$CMD" | grep -Eq 'rm[[:space:]]+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)[[:space:]]' \
  && block "rm -rf 계열 명령. 꼭 필요하면 대상 경로를 명시해 사용자가 직접 실행."
echo "$CMD" | grep -Eq 'git[[:space:]]+push[[:space:]].*(--force|[[:space:]]-f([[:space:]]|$))' \
  && block "git push --force. 협업 브랜치 이력 파괴 금지."
echo "$CMD" | grep -Eq 'git[[:space:]]+reset[[:space:]]+--hard' \
  && block "git reset --hard. 작업 내용 유실 위험 — git stash 사용."
echo "$CMD" | grep -Eq 'git[[:space:]]+clean[[:space:]].*-[a-zA-Z]*f' \
  && block "git clean -f. 미추적 파일(데이터·로컬 설정) 삭제 위험."

# ── .env / 시크릿 유출 ───────────────────────────────────────
# .env 파일 내용 출력 (cat/less/head/tail/grep/echo $(<.env) 등)
echo "$CMD" | grep -Eq '(cat|less|more|head|tail|bat|type)[[:space:]]+[^|;]*\.env([^.a-zA-Z]|$)' \
  && { echo "$CMD" | grep -q '\.env\.example' || block ".env 내용 출력. 키 확인이 필요하면 .env.example 로 변수명만 확인."; }
# .env 를 git 에 추가/커밋
echo "$CMD" | grep -Eq 'git[[:space:]]+add[[:space:]]+[^|;]*\.env([^.a-zA-Z]|$)' \
  && { echo "$CMD" | grep -q '\.env\.example' || block ".env 를 git add. 시크릿 커밋 금지."; }
echo "$CMD" | grep -Eq 'git[[:space:]]+add[[:space:]]+(-A|--all|\.)([[:space:]]|$)' \
  && [ -f .env ] && ! git check-ignore -q .env 2>/dev/null \
  && block ".env 가 ignore 되지 않은 상태에서 git add -A/. — .gitignore 먼저 확인."
# 시크릿 파일 원격 전송
echo "$CMD" | grep -Eq '(curl|wget|nc|scp)[[:space:]]+[^|;]*\.env([^.a-zA-Z]|$)' \
  && block ".env 파일 외부 전송 시도."
# memory.db / storage 사용자 DB 커밋
echo "$CMD" | grep -Eq 'git[[:space:]]+add[[:space:]]+[^|;]*(memory\.db|users\.db)' \
  && block "로컬 DB(memory.db/users.db) 커밋 금지."

exit 0
