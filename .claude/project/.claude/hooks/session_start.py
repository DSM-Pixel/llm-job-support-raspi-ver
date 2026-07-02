"""SessionStart hook: 세션 시작 시 프로젝트 현황을 간단히 안내한다.

- 현재 브랜치 / 미커밋 변경 / 활성 팀 디렉터리 등 한 눈에 알 수 있는 정보만.
- 무거운 작업/네트워크 호출은 하지 않는다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return (out.stdout or "").strip()
    except Exception:
        return ""


def main() -> int:
    lines: list[str] = ["## llm-job-support 세션 컨텍스트"]

    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch:
        lines.append(f"- 브랜치: `{branch}`")

    status = _git("status", "--porcelain")
    if status:
        n = len(status.splitlines())
        lines.append(f"- 미커밋 변경: **{n}개 파일**")
    else:
        lines.append("- 작업 트리 깨끗함")

    teams_dir = ROOT / "teams"
    if teams_dir.exists():
        teams = sorted(p.name for p in teams_dir.iterdir() if p.is_dir())
        if teams:
            lines.append(f"- 팀 워크스페이스: {', '.join(teams)}")

    proto_dir = ROOT / "prototypes"
    if proto_dir.exists():
        protos = sorted(p.name for p in proto_dir.iterdir() if p.is_dir())
        if protos:
            lines.append(f"- 프로토타입: {', '.join(protos[:6])}" + (" …" if len(protos) > 6 else ""))

    lines.append("")
    lines.append("> 도움이 필요하면 `/team-init`, `/prototype-scaffold`, `/planning-report` 사용 가능.")

    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
