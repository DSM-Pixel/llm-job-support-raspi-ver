# 통합 웹 플랫폼(FastAPI) 로컬 실행 — Windows PowerShell
# 사용법:  ./run_web.ps1            (기본 127.0.0.1:8000)
#          ./run_web.ps1 -Port 9000

param(
    [int]$Port = 8000,
    [string]$BindHost = "127.0.0.1"
)

$python = ".venv/Scripts/python"
if (-not (Test-Path $python)) {
    Write-Host "[!] .venv 가 없습니다. 먼저 'uv sync --extra web' 를 실행하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host "GNSoft AI 플랫폼 → http://$BindHost`:$Port" -ForegroundColor Cyan
& $python -m uvicorn backend.app:app --host $BindHost --port $Port --reload
