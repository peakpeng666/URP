# 依赖清单

这份清单以仓库 `main` 里的锁文件和源码为准，不是笔记本上的 `pip freeze`。笔记本当时离线，没有采集现场环境。下面凡是仓库推不出来的项目，都列在文末「需要在主人笔记本上确认」。

工作台有两套互不替换的 Python 环境，版本故意不同，安装时必须分开：

| 环境 | 解释器 | 锁文件 | 用途 |
|---|---|---|---|
| 仓库根 `.venv` | CPython 3.12.13 | `uv.lock` | 档案 / CVRP 数值任务（`src/start.sh backend`） |
| `src/lab/.venv` | CPython 3.12.13 | `src/lab/uv.lock` | 网关、求解、前端不负责的算法 |

安装命令只使用锁文件，不使用浮动版本：

```sh
uv python install 3.12.13
uv sync --locked --extra solvers --python 3.12.13
(cd src/lab && uv sync --locked --inexact --python 3.12.13)
(cd src/frontend && npm ci --engine-strict --no-audit --no-fund && npm run build)
```

`uv` 固定为 **0.12.23**。Node 固定为 **24.22.0**（官方 `linux-x64` 包 SHA256 `28ea0a438de9a13bd7891fd758eee6c7819ee8af5442dfd8d45bd65e56d4228c`，Windows x64 包 SHA256 `f9683a19877e12a9b167305c8db71040d812876359de21f0d2e97c3f321f80c3`）。仓库没有 `.nvmrc`。`src/frontend/package.json` 的 `engines.node` 是 `>=22.12.0`，CI 只写了大版本 24。部署选用当前 Node 24 的 24.22.0，npm 使用该官方包自带的 npm，`package-lock.json` 为 lockfileVersion 3。

## 直接 import、原先没写进依赖声明的包

这些名字在工作台或仿真脚本里被直接 import，以前只是别的包带进来的。现已按锁文件里的版本写进 `src/lab/pyproject.toml`，锁文件里的包版本没有改：

| import | 分发名 | 版本 | 原先从哪来 |
|---|---|---|---|
| `yaml` | PyYAML | 6.0.3 | `uvicorn[standard]` |
| `vrplib` | vrplib | 2.2.0 | `pyvrp` |
| `websockets` | websockets | 17.2 | `uvicorn[standard]`；`e2e/field_backend.py` 直接使用 |
| `starlette` | starlette | 1.8.0 | `fastapi` |

同时把原来的范围约束收成锁文件里的版本：`httpx==0.28.1`、`pillow==12.3.0`、`pyproj==3.8.0`、`python-multipart==0.0.32`、`defusedxml==0.7.1`、`opencv-python-headless==5.0.0.93`、开发依赖 `pytest==9.1.1`。

## 扫描过、不加入安装集的 import

| 名字 | 原因 |
|---|---|
| `torch` | 只出现在 `src/research` 的 NAS 试验代码。网关、档案后端和仿真会话不 import 它。 |
| `fields2cover` | 可选覆盖库。不在 PyPI 锁里。轮子路径和 SHA256 在 `src/lab/vendor/fields2cover-manifest.json`，轮子本身被 `src/lab/vendor/wheels/.gitignore` 排除。没有这份轮子时，覆盖算法使用面板里的往复基线，不假装 Fields2Cover 可用。 |
| `rclpy`、`sensor_msgs`、`geometry_msgs`、`nav_msgs`、`nav2_msgs`、`tf2_ros`、`tf2_msgs`、`rosgraph_msgs`、`visualization_msgs`、`std_msgs`、`irobot_create_msgs`、`rcl_interfaces`、`ros_gz_interfaces` | ROS 2 Humble 的系统包，给 `/usr/bin/python3`（Ubuntu 22.04 上的 3.10）用，不进 3.12 虚拟环境。 |
| 档案后端 `src/backend` | 标准库。CVRP 任务再 import 研究目录里的 `urp_research.cvrplib`，求解包来自根环境的 `solvers` extra。 |
| `urp_research.cvrp_selection` | 网关的学习特征模块 import 它，该包本身只用标准库。 |

## 工作台虚拟环境（`src/lab/uv.lock`，56 个）

```
absl-py==2.5.1
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
certifi==2026.7.22
click==8.5.0
colorama==0.4.6
contourpy==1.4.0
cycler==0.12.1
defusedxml==0.7.1
fastapi==0.143.1
fonttools==4.67.0
h11==0.16.0
httpcore==1.0.9
httptools==0.9.0
httpx==0.28.1
idna==3.20
immutabledict==4.3.1
iniconfig==2.3.1
kiwisolver==1.5.1
matplotlib==3.11.2
numpy==2.5.4
ompl==2.0.1
opencv-python-headless==5.0.0.93
opentelemetry-api==1.45.1
ortools==9.15.6755
packaging==26.3
pandas==3.0.6
pillow==12.3.0
pluggy==1.6.0
protobuf==6.33.6
pydantic==2.14.1
pydantic-core==2.50.1
pygments==2.21.0
pyparsing==3.3.3
pyproj==3.8.0
pytest==9.1.1
python-dateutil==2.9.0.post0
python-dotenv==1.2.4
python-multipart==0.0.32
pyvrp==0.14.0
pyyaml==6.0.3
scipy==1.18.1
shapely==2.2.0
six==1.17.0
starlette==1.8.0
tqdm==4.70.1
typing-extensions==4.16.0
typing-inspection==0.4.4
tzdata==2026.5
urp-lab==0.1.0
uvicorn==0.54.0
uvloop==0.23.0
vrplib==2.2.0
watchfiles==1.3.0
websockets==17.2
```

镜像和 WSL 安装使用 `--no-dev` 时不会装 `pytest` 及其只为测试服务的依赖；版本仍以锁文件为准。`uvloop` 的标记排除了 Windows。`ompl==2.0.1` 只有 Linux 与 macOS 轮子，没有 Windows 轮子，也没有 sdist。因此纯 Windows 不能 `uv sync --locked` 这套环境。

## 档案环境（根目录 `uv.lock`，28 个）

```
absl-py==2.5.1
attrs==26.1.0
colorama==0.4.6
contourpy==1.4.0
cycler==0.12.1
fonttools==4.67.0
immutabledict==4.3.1
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
kiwisolver==1.5.1
matplotlib==3.11.2
numpy==2.2.6
ortools==9.14.6206
packaging==26.3
pandas==3.0.6
pillow==13.0.0
protobuf==6.31.1
pyparsing==3.3.3
python-dateutil==2.9.0.post0
pyvrp==0.14.0
referencing==0.37.0
rpds-py==2026.9.1
six==1.17.0
tqdm==4.70.1
typing-extensions==4.16.0
tzdata==2026.5
urp-workspace==0.1.0
vrplib==2.2.0
```

注意根环境的 `numpy==2.2.6`、`ortools==9.14.6206`、`pillow==13.0.0`、`protobuf==6.31.1` 和工作台环境不同。不要合成一个环境。

`jsonschema` 由根 `pyproject.toml` 声明，档案 HTTP 服务本身不 import 它，工程检查会用到。锁文件安装它。

## 前端

直接依赖都写死在 `src/frontend/package.json`，传递依赖在 `src/frontend/package-lock.json`（284 个包记录，lockfileVersion 3）。安装只用 `npm ci`。

```
@codemirror/lang-json@6.0.2
@codemirror/lang-python@6.2.1
@fontsource/ibm-plex-mono@5.3.0
@fontsource/ibm-plex-sans@5.3.0
@foxglove/rosmsg@5.0.5
@foxglove/rosmsg2-serialization@3.1.2
@foxglove/ws-protocol@0.8.0
@noble/hashes@2.4.0
@observablehq/plot@0.6.17
@react-three/drei@10.7.9
@react-three/fiber@9.8.2
@uiw/react-codemirror@4.25.12
cmdk@1.1.1
d3-array@3.2.2
d3-scale@4.0.2
d3-shape@3.2.0
dockview-react@8.5.1
fflate@0.8.3
gltf-validator@2.0.0-dev.3.10
gzweb@3.0.2
katex@0.19.0
lucide-react@1.52.0
marked@18.1.1
react@19.3.0
react-dom@19.3.0
three@0.186.1
uplot@1.6.32
urdf-loader@0.13.1
zustand@5.0.15
```

开发依赖：`typescript@6.0.3`、`vite@8.3.3`、`vitest@5.0.3`、`@vitejs/plugin-react@6.1.2`，以及 `@types/node@24.19.1`、`@types/react@19.3.0`、`@types/react-dom@19.3.0`、`@types/three@0.186.0`、`@types/d3-array@3.2.2`、`@types/d3-scale@4.0.9`、`@types/d3-shape@3.2.0`。

`postinstall` 会跑 `node tools/patch-gzweb.mjs`，所以必须 `npm ci`，不能只拷贝 `node_modules`。运行中的 JS 基线是 `node` 执行 `src/frontend/core/routing/cvrp-solver.js`，镜像里要有 `node`，不需要再带一套 `node_modules`。

## 系统程序

工作台运行时：

| 程序 | 作用 |
|---|---|
| `bash` | `src/start.sh`、仿真启动命令 |
| CPython 3.12.13 | 网关与档案 |
| Node 24.22.0 | 构建前端；运行时执行 JS 基线 |
| `curl` | `setup/run.sh lab-stop` |
| `google-chrome` / `chromium` / `xdg-open` | 仅 `serve --open`。容器与远程浏览器不需要 |

仿真额外需要（Ubuntu 22.04，ROS 2 Humble，Gazebo Fortress / Ignition Gazebo 6）：

| 程序或包 | 作用 |
|---|---|
| `/usr/bin/python3`（3.10） | `rclpy` 会话。不能换成 3.12 |
| `ros-humble-ros-base` | rclpy 与核心消息 |
| `ros-humble-rmw-cyclonedds-cpp` | `setup/profile.sh simulation` 默认 RMW |
| `ros-humble-turtlebot4-ignition-bringup` | TB4 + Ignition |
| `ros-humble-turtlebot4-navigation` | 官方地图与 Nav2 参数 |
| `ros-humble-nav2-bringup` | Nav2 |
| `ros-humble-ros-gz-bridge` | `parameter_bridge` |
| `ros-humble-rviz2` | 可选窗口 |
| `ros-humble-foxglove-bridge` | 浏览器 ROS 视图。笔记本上的路径是 `bash src/lab/ros/native/install-ros-extras.sh`，用 `apt download` 把 `ros-humble-foxglove-bridge` 和 `ros-humble-rosx-introspection` 解到仓库内，不改 `/opt/ros` |
| `ros-humble-xacro` | 车体 URDF |
| `ignition-fortress` | `ign gazebo` |
| `libignition-gazebo6-dev` | 力矩模式按需编译关节插件，`pkg-config --modversion ignition-gazebo6` |
| `cmake`、`ninja`、`g++`、`pkg-config` | 桥接、TF、GUI 覆盖和关节插件的按需编译 |
| `ip`（iproute2） | 容器里给 `lo` 加 `239.255.0.0/16` 组播路由 |

Python 轮子是 manylinux 包，数值库的 `.so` 在轮子里。仿真的共享库在 `/opt/ros/humble/lib` 和 Ignition 的系统库。GUI 覆盖还链接 `libdl`。

## GPU

工作台和仿真源码都没有 CUDA、cuDNN 或 PyTorch 设备选择。容器说明写的是软件渲染。默认 `LIBGL_ALWAYS_SOFTWARE=1`。要用 NVIDIA GPU，在 WSL2 上安装支持 CUDA on WSL 的 Windows 驱动，Docker Desktop 使用 WSL2 后端，再叠加 `deploy/docker-compose.gpu.yml`。没有 GPU 时不要加这个文件。

## 不在 Git 里、运行时会用到的数据

| 路径 | 如何得到 |
|---|---|
| `data/backend/research.sqlite3` | **在 Git 里**。首次启动由 `tools/runtime_db.py` 复制到 `URP_API_DB`（默认 `.local-state/research.sqlite3`，容器里是卷 `/data/archive/research.sqlite3`）。不要覆盖这份冻结库。 |
| `data/packages/` | **在 Git 里**。档案的 `--import-root`。 |
| `data/research/` | **在 Git 里**。选择特征数据。 |
| `src/lab/runtime/` | 运行时生成：场景、`lab.sqlite3`、仿真日志。容器卷 `/data/lab`。 |
| `src/lab/vendor/wheels/*.whl` | 不在 Git 里。可选 Fields2Cover。完整平台附件见 `setup/README.md` 的快照说明。 |
| `setup/2026-10-15/deployment/runtime/` | 不在 Git 里。TF/GUI 覆盖库和 Foxglove 解包。`run.sh lab` 会尝试按源码重建，但验收哈希对不上时仿真会拒绝使用。 |
| Fuel 模型缓存 | 不在 Git 里。Gazebo 首次在线拉取，或从平台快照的 `fuel-cache` 组件取得。快照说明见 `setup/platform-snapshot.json`。 |
| CVRPLIB 实例正文 | 目录 JSON 在 `src/lab/urp_lab/library/data/cvrplib-catalog.json`。单题按需从 `https://galgos.inf.puc-rio.br/cvrplib` 下载到运行目录，无密钥。 |

不要把 `data/bpp`（约 206 MB）或 `data/cifar-training` 打进工作台镜像。历史 BPP 页在数据未恢复时显示无历史数据，这是现有行为。

## 环境变量

笔记本什么都不设时，行为与原来一致：只监听 `127.0.0.1`，关闭接口只接受本机连接。

| 变量 | 默认 | 含义 |
|---|---|---|
| `URP_BIND_HOST` | `127.0.0.1` | 网关监听地址。WSL 与容器设为 `0.0.0.0` |
| `URP_PORT` | `4100` | 网关端口 |
| `URP_PUBLISH_HOST` | `127.0.0.1` | 仅 Compose：宿主机发布地址 |
| `URP_EXTRA_HOSTS` | 空 | 额外允许的 Host，逗号分隔 |
| `URP_ADMIN_TOKEN` | 空 | 一旦设置，关闭接口必须带 `X-URP-Admin-Token` 或 `Authorization: Bearer` |
| `URP_ARCHIVE_URL` | `http://127.0.0.1:4180` | 档案后端 |
| `URP_ARCHIVE_AUTOSTART` | `1` | `0` 时网关不拉起档案进程 |
| `URP_API_DB` | `.local-state/research.sqlite3` | 档案库 |
| `URP_API_PORT` | `4180` | 档案端口 |
| `URP_LAB_RUNTIME` | `src/lab/runtime` | 网关运行目录 |
| `URP_FOXGLOVE_BIND` | `127.0.0.1` | Foxglove 监听地址 |
| `URP_BROWSER_HOST` | `127.0.0.1` | 页面里使用的 WebSocket 主机名 |
| `URP_BRIDGE_FIX` / `URP_TF_FIX` / `URP_GUI_FIX` | `1` | `0` 表示用未打补丁的系统实现，只作对照 |
| `URP_RMW` | `rmw_cyclonedds_cpp` | 仿真 RMW |
| `URP_ROS_DOMAIN_ID` | `139`（profile） | 验收脚本会改成隔离域 |
| `LIBGL_ALWAYS_SOFTWARE` | 容器默认 `1` | 软件 OpenGL |
| `DISPLAY` / `XAUTHORITY` | 空 | 仅本机打开 Gazebo/RViz 窗口 |

## 路径、端口、外部服务

代码里的绝对路径：

- `/opt/ros/humble`：仿真与地图。不是笔记本家目录。
- `/home/peakpeng/Desktop/URP` 和 `/home/peakpeng/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu`：只出现在已发布的平台镜像入口（`setup/platform/Dockerfile`、`tools/platform_deploy.py`）。新的 Compose 镜像用 `/opt/urp`，不再依赖这个家目录。
- `~/.cache/urp/physical-session.lock`：仿真互斥锁。
- `~/.nvm`：`setup/run.sh` 在 PATH 里没有 `node` 时才查找。

端口：`4100` 网关，`4180` 档案（只在本机，不发布），`4191` TB4 控制，`4192` 田间仿真控制，`8765` Foxglove，`9002` Gazebo WebSocket。后四个由网关在同一台机器上拉起，不是独立的 Compose 服务。

外部地址：PyPI、npm、`https://astral.sh/uv/0.12.23/install.sh`、`https://nodejs.org/dist/v24.22.0/`、`http://packages.ros.org/ros2/ubuntu`、`https://galgos.inf.puc-rio.br/cvrplib`、GitHub Release 上的平台快照。工作台和仿真源码里没有 API 密钥或令牌名。

## 需要在主人笔记本上确认

仓库推不出这些，部署没有把它们猜进安装命令：

1. 虚拟环境里装了、但源码从未 import 的 pip 包。没有 `pip freeze`。
2. 笔记本上 ROS 2、Gazebo Fortress、Foxglove `.deb` 的精确版本号。源码只写了发行版名字 Humble / Fortress。
3. 笔记本仿真是否实际用了 NVIDIA GPU 或 CUDA。源码没有 CUDA 调用；容器文档写的是软件渲染。
4. 主人日常使用的 Node 补丁号和 npm 版本。仓库只约束 `>=22.12.0`，CI 只写大版本 24。这里选用 24.22.0。
5. `--open` 所用 Chrome / Chromium 的版本。
6. Fuel 缓存里每个模型的本地状态。许可说明在平台快照的 `metadata/fuel-licenses.json`，不在普通 clone 里。
7. Fields2Cover 轮子的原始编译命令。manifest 已写明接手时轮子就在，不能声称从源码逐位重建。
