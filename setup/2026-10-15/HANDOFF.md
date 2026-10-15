# Setup 交接记录

此文件是切换模型时的历史快照。sol 接续后的实际结果见同目录 `REPORT.md`，不要将下文“尚未安装”的历史状态作为最终状态。

用户要求切换至 gpt-6.1-sol，因此当前回合在开始安装前停止。**本任务没有启动任何 APT/dpkg、npm 或 Python 包安装事务，没有待等待的安装进程。** 两个曾运行的 Git 读取/稀疏展开进程都已经成功结束。

## 已完成

- 任务已命名 Setup；操作项目 `/home/peakpeng/Desktop/URP`，远端 `peakpeng666/URP`，分支 `main`。没有接入或恢复 Redo。
- 已检查父目录和当前相关目录，没有适用的 AGENTS.md；外部参考仓库中的 AGENTS.md 不属于本次工作目录范围。
- 原项目为 partial clone + sparse checkout。已读取当前 HEAD 的部署文件，并仅追加展开 `/src/README.md`、`/src/start.sh`、`/src/checks.json`、`/src/sources.json`、`/src/backend/`、`/src/frontend/`、`/src/research/`。Git 下载了缺失对象，没有 fetch 分支更新、pull、提交或推送。前后稀疏列表已保存。
- 原有两份未跟踪文件 `src/repos/typesafe-router/.env.1password` 和 `.env.local.example` 原样保留，仅计算哈希，没有输出内容。校验结果见 `preserved-files-verified.json`。
- 没有修改已有项目源码、清单或锁文件，`git diff --stat` 为空。新增文件都在 `setup/` 内。
- 系统是 Ubuntu 22.04.5 x86_64；根分区约剩余 116 GiB。系统 Python 3.10.12，uv 0.10.11，uv 已管理 CPython 3.12.13；Node 24.14.0，npm 11.19.1；Git 2.34.1、GCC/G++ 11.4、CMake 3.22.1、Ninja 1.10.1、pkg-config 0.29.2、colcon common extensions、rosdep 0.27.0 已安装。
- `/opt/ros/humble` 和 ros-base 已安装。RViz2、Nav2、Fortress、TB4、ROS–Gazebo bridge 尚未安装。
- APT 官方来源模拟通过：443 新包，0 升级，0 删除；下载 167,322,762 字节，安装占用 929,810,432 字节。来源仅 `cn.archive.ubuntu.com`、`security.ubuntu.com`、`packages.ros.org`，均为 trusted。无需新增系统源；运行时用项目内 `apt-sources/ros2.sources`（复制自已安装的官方 ros-apt-source）限制 sourceparts，Ubuntu 仍用既有 `/etc/apt/sources.list`，不会读取其他第三方源。
- 目标包和版本见 `apt-requested-versions.txt`，完整事务来源和版本见 `apt-plan.json`；模拟日志见 `logs/apt-official-simulation.log`。包含官方 TB4 文档要求的 `ros-humble-irobot-create-nodes`。
- `check-apt-plan.py` 为只读守卫，检查精确版本、可信来源、禁止删除/替换现有包及磁盘空间；已运行通过。`install-system.sh` 已通过 `bash -n`，**未执行**。它先复查和模拟，再在日志之外 `sudo -v`，最后通过 sudo apt-get 安装并记录日志。只安装这些依赖，不升级系统。
- 沙箱内 sudo 因 no-new-privileges 不可用；一次已获自动审批的沙箱外 `sudo -n true` 返回“需要密码”，没有任何系统修改。这不是审批拒绝。用户随后主动提供了 sudo 密码；本任务未使用、未通过工具传递、未写入文件/日志或命令参数。父线程补充要求禁止通过工具传递明文凭据；继续时必须让用户在自己的本机终端密码提示中输入，不复述聊天中的敏感值。
- `nvidia-smi -L` 在受限沙箱失败，沙箱未暴露 GPU 设备，不能据此认定驱动损坏。未改驱动、安全或网络设置。

## 已确认的项目约束

- `src/research/pyproject.toml` 和 `requirements.txt`：研究核心只有标准库，不是可安装 wheel 项目，使用 `scripts/urp.py`；Python >=3.10，历史验证使用 3.12。单独创建 uv 管理的 Python 3.12 环境，不替换系统 Python，不激活全局 Conda。
- 当前展开的研究配置**没有 PyVRP 0.14 锁定项**。仅在 CVRP 实验标签中出现 `pyvrp_ils_s1e6`；需要继续查适用来源，不应凭旧历史直接添加最新版。大量 `src/repos/` 是外部参考源码，不应把其所有 requirements 都装入项目。
- 可选 NAS 直接依赖锁在 `src/research/configs/nas_requirements.txt`：NumPy 2.5.3、CPU Torch 2.14.1+cpu；`docs/NAS_FIDELITY.md` 要求独立 Python 3.12 环境，版本不匹配时拒绝运行。尚未查询这些版本仓库可用性。它属于可选训练模块，不要为完成基础安装擅自启动训练或安装全部外部参考依赖。
- 前端必须用 `npm ci --engine-strict --no-audit --no-fund` 按 `src/frontend/package-lock.json` 安装；Node >=22.12。现有 `node_modules` 可能来自旧环境，用户要求保留其他改动，建议安装前将其移动备份到 `setup/2026-10-15/backups/`（不自动删除备份），再 npm ci。
- 前端 Python `.venv` 已存在，Python 3.10.12、NumPy 2.2.6；锁文件 `src/frontend/requirements.lock` 需继续读取。官方 `scripts/setup.sh` 使用 `pip --require-hashes --only-binary=:all:`，可通过 uv 在此独立环境按同一锁安装；不要全局 sudo pip。
- 后端 `.venv` 已存在，Python 3.10.12，只有 pip/setuptools；后端全部使用标准库和 SQLite，不需要额外 pip 依赖。
- 项目数据采用链接：前端 `inputs/research/public/data`、后端 `packages` 指向未展开的 `data/`。构建可能成功但数据显示需资料包；不能声称应用完整验收，不能运行正式 53 算例。

## 接续顺序

1. 确认已切换 sol；重新检查 git 状态和正在运行的安装程序，然后从本记录继续，不重复下载/安装已存在项。
2. 阅读 `src/frontend/requirements.lock`、迁移说明及必要研究配置。保存既有环境版本；用 uv 建独立研究 Python 3.12 环境，遵照真正适用的锁文件补齐依赖。`UV_CACHE_DIR` 必须设为项目内 `setup/2026-10-15/cache/uv`，默认 `$HOME/.cache/uv` 在沙箱内只读。npm 缓存同样指定项目内。
3. 让用户在本机终端执行 `bash /home/peakpeng/Desktop/URP/setup/2026-10-15/install-system.sh`，由用户自己在 sudo 提示中输入密码。不要通过工具传递明文密码。只在守卫通过时安装。若已有不需密码的 sudo 授权，仍需正确使用系统安装权限边界。若下载版本过期，重新核对官方来源及模拟；不能改项目锁文件掩盖冲突，不要在不明确状态下重试。
4. 前端锁定安装及构建，关键 Python 导入，ROS 包发现和最小通信，Gazebo 最小启动，RViz2 和官方 TB4 仿真可用性检查。可用 DISPLAY 为 `:0`，但图形/GPU 访问尚未验证；受限时继续非图形检查并明确未测项。正式仿真、科研实验和付费模型调用均不在范围内。
5. 保存安装后版本、包差异、启动方式、回退说明、失败/未测项。无自动清理，无提交推送。

## 参考资料

- [TurtleBot4 官方仿真文档](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html)：Humble 对应 Fortress，入口 `ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py`；可传 `slam:=true nav2:=true rviz:=true`，但应先查看实际安装版本的 launch arguments。
- [Gazebo 官方 ROS 安装说明](https://gazebosim.org/docs/fortress/ros_installation/)。

没有自动审批拒绝；当前暂停原因是用户要求切换模型。完成安装、运行时检查和最终报告尚待接续。
