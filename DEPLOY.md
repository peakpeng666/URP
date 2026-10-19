# 把工作台装到另一台电脑

给搭档的 Windows 电脑用。三条路里选一条：

| 你的电脑 | 怎么做 |
|---|---|
| 装了 Docker Desktop | 走 A。这是默认路径，Windows 本机和 WSL2 都能用 |
| 只有 WSL2 Ubuntu，没有 Docker | 走 B |
| 纯 Windows，没有 WSL 也没有 Docker | 走 C。工作台和仿真都跑不起来，脚本会说明原因 |

依赖的版本和「仓库里看不到、需要主人笔记本确认」的项目在 [deploy/DEPENDENCIES.md](deploy/DEPENDENCIES.md)。

笔记本上原来的 `bash setup/run.sh lab` 仍然只监听 `127.0.0.1:4100`，不需要改命令。

## 先拿到代码

```bat
git clone https://github.com/peakpeng666/URP.git
cd URP
```

普通 clone 就包含工作台源码、前端锁文件、两套 Python 锁文件，以及档案库 `data/backend/research.sqlite3`。不要把下面这些大文件提交回仓库：

- ROS / Gazebo 的系统安装、Fuel 模型、Foxglove 解包、Fields2Cover 轮子、仿真运行库。它们不在 Git 里。取得方式见依赖清单。完整平台快照大约 7.2 GB，入口仍是 `setup/README.md` 里的 `bash setup/run.sh reproduce`，那条命令拒绝 Windows，只接受 Linux x86_64 上的本机 Docker。
- 历史 BPP 大目录 `data/bpp` 如果 clone 里已经有，工作台镜像也不会把它打进去。

磁盘：只开工作台，预留大约 8 GB。要构建带 ROS 的仿真镜像，预留 25 GB 以上。

## A. Docker Desktop

1. 安装 [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)，后端选 WSL2。安装完成后打开一次，确认托盘图标不是「Engine stopped」。
2. 在仓库根目录双击 `启动实验台.bat`，或在 PowerShell 里：

```powershell
docker compose up -d --build
```

这会构建工作台镜像：Node 24.22.0 编译前端，uv 0.12.23 按锁文件安装两套 Python 3.12.13 环境，然后在容器里启动网关。网关自己拉起档案后端。浏览器打开 http://localhost:4100/ 。健康检查是 http://localhost:4100/lab/api/health ，应返回 `"status": "ok"`。

端口只绑定在 Windows 的 `127.0.0.1`，不监听局域网。容器内部监听 `0.0.0.0`，否则 Docker 的端口转发到不了只绑定在容器 `127.0.0.1` 上的进程。不要改成 `network_mode: host`，Docker Desktop 没有 Linux 那种 host 网络。

关闭：双击 `停止实验台.bat`，或 `docker compose stop`。命名卷 `urp-lab_lab-runtime` 和 `urp-lab_archive-data` 会保留场景、运行库和档案库。`docker compose down` 也保留卷。删卷才会丢运行数据：`docker compose down -v`。

更新：

```powershell
git pull
docker compose up -d --build
```

回退：`git checkout` 到上一提交后再执行同一条构建命令。旧卷还在，所以运行库不会被这次构建清掉。

### 仿真镜像

工作台镜像没有 ROS，页面里的仿真会显示 ROS 不可用。要在容器里装 ROS 2 Humble 和 Gazebo Fortress：

```powershell
docker compose -f deploy/docker-compose.sim.yml up -d --build
```

第一次会很久，镜像很大。构建完成并健康之后，浏览器仍是 http://localhost:4100/ 。Foxglove 和 Gazebo 的页面套接字发布在 Windows 的 `127.0.0.1:8765` 和 `127.0.0.1:9002`。

这台云端 Linux 虚拟机没有把这个仿真镜像构建完，也没有跑通 Gazebo。原因写在下面「这次没在真机上验证的部分」。

仿真还依赖仓库里没有的验收二进制（桥接、TF、GUI 覆盖）。默认 `URP_BRIDGE_FIX=1`。新机器上现编译的二进制和主人笔记本的哈希不一致时，仿真会拒绝启动，而不是悄悄换一套。不要为了先跑起来把这三个开关改成 0，除非明确是在做对照实验。

### GPU

默认软件渲染（`LIBGL_ALWAYS_SOFTWARE=1`），没有显卡也能开工作台。Gazebo 若要用 NVIDIA GPU：

1. Windows 安装支持 [CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html) 的驱动。不需要在 WSL 里再装一套 Linux 驱动。
2. Docker Desktop 使用 WSL2 后端。
3. 在仿真镜像上叠加 GPU 文件：

```powershell
docker compose -f deploy/docker-compose.sim.yml -f deploy/docker-compose.gpu.yml up -d --build
```

没有 NVIDIA 设备时不要加第二个文件，否则容器起不来。

## B. 只有 WSL2

1. 管理员 PowerShell：`wsl --install -d Ubuntu`。说明见 [安装 WSL](https://learn.microsoft.com/windows/wsl/install)。
2. 进入 Ubuntu，装一次编译和下载所需的基础包（脚本在缺少 `curl` 时也会用 `sudo apt-get` 安装 `curl`、`ca-certificates`）：

```sh
cd /mnt/c/Users/你的用户名/URP
bash setup/wsl/setup.sh
bash setup/wsl/run-lab.sh
```

`setup.sh` 把 uv 0.12.23 和 Node 24.22.0 装到 `~/.local`，用 CPython 3.12.13 按锁文件创建两个虚拟环境，并构建前端。`run-lab.sh` 让网关在 WSL 里监听 `0.0.0.0:4100`，Windows 浏览器通过 WSL 的 localhost 转发打开 http://localhost:4100/ 。

关闭要在 WSL 里执行，这样连接才是本机回环，关闭接口才会接受：

```sh
bash setup/run.sh lab-stop
```

仿真：在这份 Ubuntu 22.04 里自行安装依赖清单中的 ROS Humble 与 Ignition Fortress 软件包，并准备 `/opt/ros/humble`。`setup.sh` 不安装它们。装好之前，规划页面可用，仿真启动会说明 ROS 不可用。

WSL 内存。在 Windows 用户目录的 `.wslconfig` 里限制，避免 Gazebo 把内存吃满：

```ini
[wsl2]
memory=8GB
processors=4
localhostForwarding=true
swap=4GB
```

只做规划时 8 GB 够用。要跑 Gazebo，把 `memory` 提到 16 GB，然后在 PowerShell 执行 `wsl --shutdown` 再重新打开 Ubuntu。

## C. 纯 Windows

双击 `启动实验台.bat` 时，如果既没有 Docker 也没有 WSL，脚本会停下来并给出上面两个安装链接。

不能在原生 Windows 上按锁文件安装工作台：`ompl==2.0.1` 没有 Windows 轮子。ROS 2 Humble 与 Gazebo Fortress 也不是这条代码路径能在原生 Windows 上启动的。请安装 Docker Desktop 或 WSL2。

## 关闭接口

`POST /lab/api/shutdown` 默认只接受来自 `127.0.0.1` 或 `::1` 的连接。容器里从 Windows 转发进来的连接不是回环，所以从浏览器或宿主机 `curl` 这个地址会得到 403。这是故意的。关容器用 `docker compose stop`。关 WSL 里的进程用 WSL 内部的 `bash setup/run.sh lab-stop`。

只有在必须从另一台机器调用关闭接口时才设置 `URP_ADMIN_TOKEN`。设置之后，包括本机在内的所有关闭请求都要带这个值。页面上的求解和仿真按钮不使用这个接口。

## 排错

| 现象 | 处理 |
|---|---|
| 浏览器打不开 localhost:4100 | Docker 引擎是否已启动；WSL 是否在跑 `run-lab.sh`；Windows 防火墙是否拦截了专用网络上的 Docker |
| 页面 403，提示拒绝的 Host | 用 http://localhost:4100/ 打开。若用局域网 IP，把该主机名写入 `URP_EXTRA_HOSTS`，并把 `URP_PUBLISH_HOST` 改成 `0.0.0.0`。个人电脑不需要这样做 |
| 端口被占用 | 先走停止脚本。不要按进程名批量结束进程 |
| `sh` 脚本报 `$'\r'` | 仓库用 `.gitattributes` 把 `*.sh` 保持为 LF。若仍出现，在 WSL 里 `dos2unix setup/wsl/*.sh setup/run.sh`，不要在记事本里保存这些脚本 |
| WSL 里仿真中途被系统杀掉 | 提高 `.wslconfig` 的 `memory`，执行 `wsl --shutdown` |
| 仿真提示 ROS 不可用 | 当前是工作台镜像或尚未在 WSL 安装 ROS。见上文仿真镜像 |
| 仿真提示桥接或覆盖指纹不符 | 新编译结果和主人笔记本的验收二进制不一致。不要改成成功。需要平台快照里的 `compiled-and-wheels`，或在主人机器上保留原来的 `setup/2026-10-15/deployment/runtime` |
| `ompl` 在 Windows 上安装失败 | 预期行为。改走 A 或 B |
| 组播 `Network is unreachable` | 容器入口会尝试 `ip route replace 239.255.0.0/16 dev lo`。失败时规划仍可用，Gazebo 发现会失败。需要 `NET_ADMIN`，Compose 已经加上 |

## 这次验证了什么

在构建这次改动的 Linux 虚拟机上：

- 工作台访问控制的单元测试（关闭接口、默认仍是本机）。
- `bash setup/wsl/setup.sh` 是否能在这台 Ubuntu 上装好锁文件里的环境并构建前端。
- `docker compose up` 之后，首页和 `/lab/api/health` 是否返回 200，以及从宿主机调用关闭接口是否返回 403。

没有在真实 Windows、WSL2 或 NVIDIA GPU 上点过界面。仿真镜像没有在这台虚拟机里构建到 Gazebo 能跑：它需要 Ubuntu 22.04 的 ROS Humble 与 Ignition，体积大，而且验收用的桥接二进制不在 Git 里，现场重编译会被指纹拒绝。工作台镜像里的仿真按钮会如实显示 ROS 不可用，不会把演示数据写成成功。
