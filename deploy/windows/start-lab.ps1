# Start the workbench on a Windows PC. Docker Desktop is preferred, then WSL2.
# Native Windows cannot install the locked lab environment: ompl 2.0.1 has no Windows wheel.
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
if (Test-DockerEngine) {
    docker compose -f (Join-Path $Root 'deploy\docker-compose.yml') up -d --build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (Wait-Health $health 40) { Start-Process 'http://localhost:4100/' }
    else { Write-Warning '容器已启动，但健康检查尚未返回。请看 docker compose logs。' }
    exit 0
}

$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if ($wsl) {
    $wslPath = (wsl.exe -e wslpath -a $Root).Trim()
    if (-not $wslPath) { throw 'wslpath 没有返回仓库路径。' }
    Start-Process wsl.exe -ArgumentList @('-e', 'bash', '-lc', "cd '$wslPath' && bash setup/wsl/run-lab.sh")
    if (Wait-Health $health 300) { Start-Process 'http://localhost:4100/' }
    else { Write-Warning '已在新窗口启动 WSL。若浏览器打不开，请看该窗口里的报错。' }
    exit 0
}

Write-Host @'
没有找到可用的 Docker Desktop，也没有 WSL。

纯 Windows 不能按锁文件安装工作台：ompl==2.0.1 只有 Linux 与 macOS 的轮子，没有 Windows 轮子。
ROS 2 Humble 与 Gazebo Fortress 也不能在原生 Windows 上按本仓库的方式运行。

请安装下面之一后重新双击「启动实验台」：
  Docker Desktop（WSL2 后端）  https://docs.docker.com/desktop/setup/install/windows-install/
  WSL2 Ubuntu                   https://learn.microsoft.com/windows/wsl/install
'@
exit 2
