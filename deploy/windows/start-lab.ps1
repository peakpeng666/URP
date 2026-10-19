# Optional Windows convenience launcher. It does not run the stack natively.
# Docker Desktop (WSL2 backend) starts the simulation compose file.
# Otherwise it asks WSL2 Ubuntu to run setup/ubuntu/run-lab.sh.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root

function Test-DockerEngine {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { return $false }
    docker info *> $null
    return ($LASTEXITCODE -eq 0)
}

function Wait-Health {
    param([string]$Url, [int]$Attempts = 60)
    for ($i = 0; $i -lt $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return $true }
        } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

$health = 'http://127.0.0.1:4100/lab/api/health'
$compose = Join-Path $Root 'deploy\docker-compose.sim.yml'
if (Test-DockerEngine) {
    $image = if ($env:URP_IMAGE_TAG) { "ghcr.io/peakpeng666/urp-sim:$($env:URP_IMAGE_TAG)" } else { 'ghcr.io/peakpeng666/urp-sim:deploy' }
    docker pull $image
    if ($LASTEXITCODE -ne 0) {
        docker image inspect $image *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host '匿名拉取失败。不要执行 docker login。'
            Write-Host '主人打开 https://github.com/users/peakpeng666/packages/container/urp-sim/settings'
            Write-Host 'Package settings → Change package visibility → Public。urp-bench 同样操作。'
            exit 1
        }
    }
    docker compose -f $compose up -d --no-build --pull never
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (Wait-Health $health 90) { Start-Process 'http://localhost:4100/' }
    else { Write-Warning '容器已启动，但健康检查尚未返回。请看 docker compose logs。' }
    exit 0
}

if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    $wslPath = (wsl.exe -e wslpath -a $Root).Trim()
    if (-not $wslPath) { throw 'wslpath 没有返回仓库路径。' }
    Start-Process wsl.exe -ArgumentList @('-e', 'bash', '-lc', "cd '$wslPath' && bash setup/ubuntu/run-lab.sh")
    if (Wait-Health $health 300) { Start-Process 'http://localhost:4100/' }
    else { Write-Warning '已在新窗口启动 WSL。若浏览器打不开，请看该窗口里的报错。' }
    exit 0
}

Write-Host '没有 Docker，也没有 WSL。请安装 Docker Desktop（WSL2 后端）或 WSL2 Ubuntu 22.04。'
Write-Host 'https://docs.docker.com/desktop/setup/install/windows-install/'
Write-Host 'https://learn.microsoft.com/windows/wsl/install'
exit 1
