# Stop the simulation stack. Docker receives SIGTERM. WSL uses the loopback shutdown API.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root

function Stop-Compose {
    param([string]$File)
    if (-not (Test-Path $File)) { return $false }
    $running = docker compose -f $File ps --status running -q
    if ($LASTEXITCODE -ne 0) { return $false }
    if ($running) {
        docker compose -f $File stop
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        return $true
    }
    return $false
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    $stopped = $false
    if (Stop-Compose (Join-Path $Root 'deploy\docker-compose.sim.yml')) { $stopped = $true }
    if (Stop-Compose (Join-Path $Root 'deploy\docker-compose.yml')) { $stopped = $true }
    if ($stopped) { exit 0 }
}

if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    wsl.exe -e bash -lc "curl --fail-with-body -sS -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:4100/lab/api/shutdown"
    exit $LASTEXITCODE
}

Write-Host '没有正在由 Docker 或 WSL 托管的工作台可关。'
exit 1
