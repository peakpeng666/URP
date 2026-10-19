# 把工作台和仿真装到另一台电脑

仓库 `peakpeng666/URP` 是公开的。镜像和 Release 附件也按公开来用。默认路径不登录、不提示令牌。

三条路，都包含 ROS 2 Humble 和 Gazebo Fortress。没有纯 Windows 路径。

| 你的电脑 | 安装器怎么做 |
|---|---|
| Docker Desktop（Windows 的 WSL2 后端，或 Linux 上的 Docker） | A。不克隆仓库。拉取 `ghcr.io/peakpeng666/urp-sim:deploy` 后启动 |
| WSL2 里的 Ubuntu 22.04，不用 Docker | B。浅克隆，排除 `src/repos`、`data/bpp`、`data/cifar-training` |
| 原生 Ubuntu 22.04 | C。与 B 同一套 `setup/ubuntu/setup.sh` |

B 和 C 发现是 WSL 时才使用软件渲染和 `0.0.0.0` 监听。原生 Ubuntu 不设置 `LIBGL_ALWAYS_SOFTWARE`。主人笔记本上的 `bash setup/run.sh lab` 仍然只监听 `127.0.0.1:4100`，也不设置 `URP_SIM_PROFILE`。

依赖版本在 [deploy/DEPENDENCIES.md](deploy/DEPENDENCIES.md)。第三方许可在 [deploy/THIRD_PARTY.md](deploy/THIRD_PARTY.md)。

## 一条命令

Linux、WSL Ubuntu 或任何能跑 bash 和 Docker 的机器：

```sh
curl -fsSL https://raw.githubusercontent.com/peakpeng666/URP/deploy/install.sh | bash
```

Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/peakpeng666/URP/deploy/install.ps1 | iex
```

PowerShell 里 `docker info` 成功时，直接在 Windows 拉取镜像，不克隆约 3 GB 的仓库，也不进发行版。没有 Docker 时，它安装或使用 WSL 的 Ubuntu 22.04，再执行上面的 bash。第一次打开 Ubuntu 要先建一个 Linux 用户；建完后把同一条命令再执行一次。

装好之后：

```sh
urp up        # 已装过就再启动
urp down      # 停止，保留数据卷
urp update    # Docker：重新拉取。Ubuntu：更新浅克隆并重装后启动
urp status    # 健康检查
urp fuel      # 可选。从 fuel.gazebosim.org 下载 warehouse / depot 模型
```

`~/.local/bin` 不在 PATH 里时，用完整路径 `~/.local/bin/urp`。Windows 上后来的命令是再执行一次 `install.ps1`，参数用 `status`、`down`、`update` 或 `fuel`。

浏览器打开 http://localhost:4100/ 。健康检查 http://localhost:4100/lab/api/health 应返回 `"status":"ok"`。Foxglove 和 Gazebo WebSocket 在 `127.0.0.1:8765` 和 `127.0.0.1:9002`。

不要使用 `network_mode: host`。DDS 使用 `setup/cyclonedds.xml`：关闭组播，只在 `lo` 上向 `localhost` 做单播发现，并保留 `ROS_LOCALHOST_ONLY=1`。不需要 `NET_ADMIN`。

只要规划、不要 ROS 时，在已经克隆的仓库里：

```sh
docker compose -f deploy/docker-compose.yml up -d
```

这拉的是 `ghcr.io/peakpeng666/urp-bench`。默认那条命令拉的是带仿真的 `urp-sim`。

## 主人做一次的公开设置

Actions 用 `GITHUB_TOKEN` 推送的包默认是私有的，工作流里的接口经常返回 403，不能代替下面的点击。镜像推上去之后：

1. 打开 https://github.com/users/peakpeng666/packages/container/urp-sim/settings
2. **Package settings → Change package visibility → Public**
3. 对 `urp-bench` 做同样的操作：https://github.com/users/peakpeng666/packages/container/urp-bench/settings
4. 若页面写着没有关联仓库：**Connect repository → peakpeng666/URP**。工作流和 Dockerfile 都写了 `org.opencontainers.image.source=https://github.com/peakpeng666/URP`。

推送发生在 `deploy` 分支和 `v*` 标签。`deploy` 得到 `:deploy` 和提交号；`v*` 得到版本号和 `:latest`。工作流是 `.github/workflows/images.yml`。

在这一步完成之前，`docker pull` 会失败。安装器打印上面的地址然后退出。它不会执行 `docker login`，也不会要搭档的令牌。

不要把 Fuel 缓存上传为 Release。可以公开上传的只有 Fields2Cover 轮子，并且必须连同 BSD 声明：

```sh
bash deploy/upload-assets.sh vYYYYMMDD
```

没有轮子时这条命令不上传任何东西。

## 浅克隆里有什么

没有 Docker 时，安装器把检出放在 `~/.local/share/urp/src`：

```sh
git clone --depth 1 --filter=blob:none --sparse --branch deploy https://github.com/peakpeng666/URP.git
```

然后排除 `src/repos`、`data/bpp`、`data/cifar-training`。Docker 路径只下载 compose 文件到 `~/.local/share/urp`（Windows 是 `%LOCALAPPDATA%\urp`）。

## GPU

镜像默认 `LIBGL_ALWAYS_SOFTWARE=1`。要用 NVIDIA：

```sh
URP_GPU=1 urp up
```

Windows 使用支持 CUDA on WSL 的驱动，不要在 WSL 里再装 Linux 驱动。没有 NVIDIA 设备时不要加 `URP_GPU=1`。原生 Ubuntu 不走这个变量。

## Fuel 与许可

`maze` 不引用 Fuel，一条命令起来就能开这个世界。

`warehouse` 和 `depot` 需要使用者自己向 https://fuel.gazebosim.org 下载。`urp fuel` 做这件事，并把缓存挂进容器或写到检出的 `setup/2026-10-15/cache/ignition-fuel`。这是使用者自己的副本，不是我们再分发。

不能放进公开镜像或公开 Release：

| 模型 | 许可 |
|---|---|
| OpenRobotics Warehouse 5 | CC BY-NC-ND 4.0 |
| MovAi shelf_big 2 | CC BY-NC-ND 4.0 |
| MovAi shelf 1 | CC BY-NC 4.0 |

Foxglove bridge 是 MIT，rosx_introspection 是 MPL-2.0，随镜像里的 apt 包安装，许可文件保留。Fields2Cover 是 BSD-3-Clause，轮子不在镜像里。细节在 `deploy/THIRD_PARTY.md`。

## 指纹

笔记本验收文件不改。系统库与验收记录一致时，只接受原来的二进制。镜像和别的机器在 `URP_SIM_PROFILE=image` 时使用编译出来的 `profile.json`。`URP_BRIDGE_FIX=0`、`URP_TF_FIX=0`、`URP_GUI_FIX=0` 只是对照开关。

发布出去的 `urp-sim` 在构建时运行 `deploy/record-sim-profiles.py`，所以镜像里的指纹就是那次构建的产物。本地另编的二进制不会被拿去冒充已发布镜像。

## 关闭接口

`POST /lab/api/shutdown` 默认只接受回环地址。从 Windows 经 Docker 转发进来的连接会得到 403。关容器用 `urp down` 或 `docker compose stop`。关 WSL 或本机进程要在那个 Linux 里执行 `urp down`，这样连接才是回环。设置 `URP_ADMIN_TOKEN` 之后，所有关闭请求都要带 `X-URP-Admin-Token` 或 `Authorization: Bearer`。

卷 `urp-lab_lab-runtime` 和 `urp-lab_archive-data` 在 `urp down` 之后还在。`docker compose down -v` 才删卷。

Windows 上也可以双击 `启动实验台.bat`。它只调用 Docker 或 `wsl`，不在 Windows 里安装 Python。

## 自己构建

公开镜像还没推送，或要改 Dockerfile 时：

```sh
docker compose -f deploy/docker-compose.sim.yml -f deploy/docker-compose.sim-build.yml build
```

构建需要仓库，产物的名字就是 `ghcr.io/peakpeng666/urp-sim:deploy`。日常安装不要走这条。

## 排错

| 现象 | 处理 |
|---|---|
| `docker pull` 要求登录或 403 | 主人把包改成 Public。搭档不要 `docker login` |
| 浏览器打不开 localhost:4100 | Docker 引擎是否已启动；WSL 里 `urp status` |
| 页面 403，提示拒绝的 Host | 用 http://localhost:4100/ |
| `sh` 脚本报 `$'\r'` | `*.sh` 在 `.gitattributes` 里是 LF |
| WSL 里仿真被杀掉 | 把 `setup/ubuntu/wslconfig.example` 复制为 Windows 用户目录的 `.wslconfig`，然后 `wsl --shutdown` |
| warehouse 或 depot 报世界资源不完整 | `urp fuel`。maze 不需要 |
| 指纹不符 | 镜像里应已有 profile。源码被改过才会拒绝 |
| Ubuntu 不是 22.04 | 没有 Docker 时安装器会停。Humble 只装在 22.04 |

## 仿真怎么试

工作台起来之后，TB4 用官方 `maze`（无 GUI）：

```sh
curl -sS -X POST http://127.0.0.1:4100/lab/api/services/sim/start \
  -H 'content-type: application/json' \
  -d '{"world":"maze","gui":false,"rviz":false,"localization":"ground_truth"}'
```

等到 `GET /lab/api/services` 里仿真为运行，并且 `127.0.0.1:8765` 与 `127.0.0.1:9002` 能连上。田间仿真要先有一份已验算通过的多车方案，再 `POST /lab/api/fieldsim`。
