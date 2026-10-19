# Stop the workbench. Docker receives SIGTERM. WSL uses the loopback shutdown API.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose -f (Join-Path $Root 'deploy\docker-compose.yml') ps --status running -q *> $null
    if ($LASTEXITCODE -eq 0) {
        $running = docker compose -f (Join-Path $Root 'deploy\docker-compose.yml') ps --status running -q
        if ($running) {
            docker compose -f (Join-Path $Root 'deploy\docker-compose.yml') stop
            exit $LASTEXITCODE
        }
    }
}

$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if ($wsl) {
    wsl.exe -e bash -lc "curl --fail-with-body -sS -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:4100/lab/api/shutdown"
    exit $LASTEXITCODE
}

Write-Host '没有正在由 Docker 或 WSL 托管的工作台可关。'
exit 1
