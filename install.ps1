# Public Windows installer. No GitHub login and no docker login.
#   irm https://raw.githubusercontent.com/peakpeng666/URP/deploy/install.ps1 | iex
# Docker Desktop pulls ghcr.io/peakpeng666/urp-sim and does not clone the repository.
# Without Docker, the same bash installer runs inside WSL Ubuntu 22.04.
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'update', 'status', 'fuel')]
    [string]$Command = 'up'
)

$ErrorActionPreference = 'Stop'
$Raw = 'https://raw.githubusercontent.com/peakpeng666/URP/deploy'
$Image = if ($env:URP_IMAGE_TAG) { "ghcr.io/peakpeng666/urp-sim:$($env:URP_IMAGE_TAG)" } else { 'ghcr.io/peakpeng666/urp-sim:deploy' }
$State = Join-Path $env:LOCALAPPDATA 'urp'
$Health = 'http://127.0.0.1:4100/lab/api/health'
$Page = 'http://localhost:4100/'

function Show-Visibility {
    Write-Host @'
匿名拉取 ghcr.io/peakpeng666/urp-sim 失败。不要执行 docker login，也不要申请令牌。
主人在浏览器里做一次：
  https://github.com/users/peakpeng666/packages/container/urp-sim/settings
  Package settings → Change package visibility → Public
  对 urp-bench 重复一次。
若未关联仓库：Connect repository → peakpeng666/URP。
'@
}

function Test-DockerEngine {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { return $false }
    try {
        docker info *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Get-ComposeFile {
    New-Item -ItemType Directory -Force -Path (Join-Path $State 'deploy') | Out-Null
    $names = @('docker-compose.sim.yml', 'docker-compose.gpu.yml', 'docker-compose.fuel.yml', 'docker-compose.display.yml')
    foreach ($name in $names) {
        $out = Join-Path $State "deploy\$name"
        Invoke-WebRequest -UseBasicParsing -Uri "$Raw/deploy/$name" -OutFile $out
    }
    return (Join-Path $State 'deploy\docker-compose.sim.yml')
}

function Wait-Health {
    param([int]$Attempts = 90)
    for ($i = 0; $i -lt $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Health -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and $response.Content -match '"status":"ok"') { return $true }
        } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Invoke-Compose {
    param([string[]]$ComposeArgs)
    $files = @('-f', (Join-Path $State 'deploy\docker-compose.sim.yml'))
    if ($env:URP_GPU -eq '1') { $files += @('-f', (Join-Path $State 'deploy\docker-compose.gpu.yml')) }
    if ($env:URP_DISPLAY -eq '1') { $files += @('-f', (Join-Path $State 'deploy\docker-compose.display.yml')) }
    $fuel = if ($env:URP_FUEL_DIR) { $env:URP_FUEL_DIR } else { Join-Path $State 'fuel' }
    if (Test-Path (Join-Path $fuel 'fuel.gazebosim.org')) {
        $env:URP_FUEL_DIR = $fuel
        $files += @('-f', (Join-Path $State 'deploy\docker-compose.fuel.yml'))
    }
    & docker compose @files @ComposeArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-DockerPath {
    param([string]$Action)
    Get-ComposeFile | Out-Null
    if ($Action -eq 'down') {
        Invoke-Compose @('stop')
        Write-Host "容器已停止。数据卷还在。"
        return
    }
    if ($Action -eq 'status') {
        Invoke-Compose @('ps')
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Health
        Write-Host $response.Content
        return
    }
    if ($Action -eq 'up' -or $Action -eq 'update' -or $Action -eq 'fuel') {
        $pulled = $true
        docker pull $Image
        if ($LASTEXITCODE -ne 0) {
            docker image inspect $Image *> $null
            if ($LASTEXITCODE -ne 0) {
                Show-Visibility
                exit 1
            }
            Write-Host "注册表暂时拉不到，使用本机已有的 $Image。"
            $pulled = $false
        }
        if ($Action -eq 'fuel') {
            $bash = Get-Command bash -ErrorAction SilentlyContinue
            $dest = Join-Path $State 'fuel'
            $script = Join-Path $State 'deploy\fetch-fuel.sh'
            Invoke-WebRequest -UseBasicParsing -Uri "$Raw/deploy/fetch-fuel.sh" -OutFile $script
            if ($bash) {
                & bash $script $dest
                if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            } else {
                Write-Host "下载 Fuel 需要 bash，或在 WSL Ubuntu 22.04 里执行 urp fuel。maze 不需要 Fuel。"
                exit 1
            }
            $env:URP_FUEL_DIR = $dest
        }
        if (-not $pulled) { }
        Invoke-Compose @('up', '-d', '--no-build', '--pull', 'never', '--remove-orphans')
        if (Wait-Health) { Start-Process $Page }
        else { Write-Warning "容器已启动，但健康检查尚未返回。请看 docker compose logs。" }
        Write-Host $Page
        return
    }
}

function Test-WslUbuntu {
    wsl.exe -d Ubuntu-22.04 -e true
    return ($LASTEXITCODE -eq 0)
}

function Invoke-WslPath {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        Write-Host "没有 Docker，也没有 wsl.exe。请安装 Docker Desktop（WSL2 后端）或 WSL2 Ubuntu 22.04。"
        Write-Host "https://docs.docker.com/desktop/setup/install/windows-install/"
        Write-Host "https://learn.microsoft.com/windows/wsl/install"
        exit 1
    }
    if (-not (Test-WslUbuntu)) {
        Write-Host "没有 Docker。正在安装 WSL2 的 Ubuntu 22.04。可能需要管理员权限；若提示重启，重启后重新执行同一条命令。"
        wsl.exe --install -d Ubuntu-22.04
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        if (-not (Test-WslUbuntu)) {
            Write-Host "Ubuntu 22.04 还不能执行命令。第一次打开它时要创建一个 Linux 用户，完成后再执行这一条命令。"
            exit 1
        }
    }
    $remote = "curl -fsSL $Raw/install.sh | bash -s -- $Command"
    wsl.exe -d Ubuntu-22.04 -e bash -lc $remote
    exit $LASTEXITCODE
}

if (Test-DockerEngine) {
    Invoke-DockerPath $Command
    exit 0
}

Invoke-WslPath
