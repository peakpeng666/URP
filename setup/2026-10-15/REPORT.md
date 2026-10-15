# Setup 实际结果

> 本文件是最初依赖安装阶段的历史记录。后续前端构建修复、硬件实测、追加 7 个 CycloneDDS 包、TF 死锁复现与当前暂停项，请以 [本轮交付报告](deployment/REPORT.md) 为准；最终累计新增 450 包、0 升级、0 删除，导航稳定性尚未验收。

记录时间：2026-10-15 UTC。工作目录 `/home/peakpeng/Desktop/URP`。任务范围为依赖安装与最小验证；没有运行正式算例、训练或付费模型调用，没有提交或推送。

**依赖安装已完成：系统新增 443 包、0 升级、0 删除。Python、后端、ROS、Gazebo 最小运行与 RViz 渲染通过；修正验证探针后，TurtleBot4 两次独立启动均激活控制器并连续观察通过。前端标准构建仍缺历史数据，整套系统尚未完整验收。**

## 已完成与证据

| 项目 | 实际结果 | 证据 |
|---|---|---|
| 科研 Python | uv 创建 `src/research/.venv`，CPython 3.12.13；按当前清单，核心无第三方运行依赖 | `logs/research-venv.log`、`logs/research-imports.log` |
| 科研最小检查 | 核心模块导入、CLI 帮助和三个微型合成例通过；模型调用为 0 | `research-smoke.json`、`logs/research-cli-help.log` |
| 前端 Python | 原有 Python 3.10.12 / NumPy 2.2.6 符合带 SHA256 的 `requirements.lock`，uv 检查无需重复安装；导入、数组计算、依赖兼容检查通过 | `logs/frontend-python-install.log`、`logs/frontend-python-import.log`、`logs/frontend-python-check.log` |
| Node 前端 | Node 24.14.0 / npm 11.19.1；`npm ci --engine-strict --no-audit --no-fund` 成功，安装 67 包；使用锁文件内已有 npmmirror 地址和 integrity | `logs/frontend-npm-ci.log`、`frontend-npm-after.json` |
| 标准前端构建 | TypeScript 检查通过，Vite 转换 2125 模块后在复制悬空的 `public/data` 链接时失败 | `logs/frontend-build.log` |
| 额外源码打包检查 | 不复制 public 数据的 Vite 打包成功；产物在 `runtime/frontend-dist`，仅用于验证源码打包，不代表数据页面验收 | `logs/frontend-code-bundle.log` |
| 后端 | 原有 Python 3.10.12 / SQLite 3.37.2；模块导入、临时独立数据库、真实本机 HTTP 健康接口及空记录查询通过，服务已关闭 | `backend-smoke.json`、`logs/backend-imports.log` |
| Humble 基础 | 系统 Python 3.10 成功导入 rclpy；发现 187 个 ROS 包；两个临时节点成功发现发布者并收发测试消息，节点已退出 | `logs/ros-discovery.log`、`ros-smoke.json` |
| 系统安装 | 用户在桌面可见终端自行输入 sudo；安装退出码 0。实际新增 443 包、0 升级、0 删除 | `logs/apt-install.log`、`runtime/system-install.exit-code`、`dpkg-diff.json` |
| Gazebo / RViz | Fortress 实际版本 6.18.0，五步无图形物理运行通过；RViz2 建立 OpenGL 4.6 渲染，按计划中断退出 | `logs/system-verification.log`、`logs/gazebo-version.log`、`logs/gazebo-minimal.log`、`logs/rviz-render.log` |
| 官方 TurtleBot4 | 原探针失败证据保留；改为被动等待后单次查询，两次独立启动的两个控制器均 active，持续观察十秒，时钟/里程计/激光均收到 | `diagnostics/VALIDATION.md`、`turtlebot4-passive-smoke.json`、`turtlebot4-passive-confirm-smoke.json` |
| 文件保护 | 已有锁文件和两份用户未跟踪文件哈希未变，已有受版本控制源码无 diff；旧 node_modules 已移动备份 | `preserved-files-final.json`、`git-status-after.txt`、`backups/frontend-node_modules-before` |

版本记录在 `versions-after.json`、`system-versions-after.tsv`；已有 Python 环境安装前记录在 `frontend-python-before.json`、`backend-python-before.json`。系统安装前后完整清单为 `dpkg-before.tsv`、`dpkg-after.tsv`，差异见 `dpkg-diff.json`。原有系统 Python、Node 与构建工具版本未变。`dpkg --audit` 无输出，未发现未配置包。

当前展开的研究清单未要求 PyVRP；旧历史提及的 PyVRP 0.14 只在实验算法标签中出现，没有找到适用锁定安装清单，因此未另行添加。可选 NAS 的精确 NumPy/Torch 依赖只用于独立训练环境，本次未安装，也未验证其仓库可用性。大量外部论文仓库的独立依赖不属于核心运行环境。

## 系统安装与验证结果

系统安装已经完成，不需要用户再次执行安装。使用 `interactive-install.sh` 在可见 GNOME 终端提示 sudo，用户直接输入密码，模型未接触输入。安装退出码保存为 0；目前可见安装终端可能仍在等待用户按 Enter 关闭，它已经没有运行 APT/dpkg。

本次窗口错误地硬编码 `/usr/bin/gnome-terminal`，绕过了已配置的 Ghostty。已只读核对并为本任务新增遵循默认适配器的后续入口：

```bash
bash /home/peakpeng/Desktop/URP/setup/2026-10-15/launch-system.sh
```

此命令仅作为未来需要重开 Setup 终端时的入口，当前不要启动第二份安装。详见 `terminal-audit.md`。系统 alternatives 仍指向旧 GNOME，是全量替换仍需审查的入口；本任务没有改系统终端设置或 macOS-Desktop 项目。

安装时再次检查官方来源、精确版本、空间与事务计划，守卫通过。已安装 RViz2、Nav2、Gazebo Fortress、官方 TurtleBot4 仿真、Create3 nodes 与 Humble 对应桥接。来源限已有 Ubuntu 官方源和项目内复制的官方 ROS 源，未改系统源配置。没有系统升级、驱动安装、Docker、Jazzy 或 Harmonic 第二套安装。聊天中的凭据未使用、未传入工具、未落盘。没有审批拒绝或待处理认证。

已实际执行并通过的非图形最小检查可复用：

```bash
bash /home/peakpeng/Desktop/URP/setup/2026-10-15/verify-system.sh
```

它检查 ROS 包发现和收发、Gazebo 无外部模型的五步物理运行、RViz 可执行文件及 TurtleBot4 launch 参数。另已启动 RViz2 验证实际渲染，NVIDIA 显卡与驱动工作正常（`graphics-check.json`），无需重装驱动。

TurtleBot4 首次短暂启动收到了 `/clock`、`/odom`、`/scan`，但观察过早结束，不能证明控制器就绪。第二次等待控制器激活时，只有 joint_state_broadcaster 进入 active；服务响应抛出 `failed to send response: cannot publish data`，栈经过 controller_manager/rclcpp，Gazebo 后续退出，diffdrive_controller 未激活。记录为 **INCOMPLETE**。QML 引用/弃用、控制更新周期快于仿真周期等提示也保留在日志。已修正本测试 Fuel 缓存目录缺失问题，未修改官方系统包或仿真配置。

**后续诊断已修正上述结论：** 原探针在初始化期无节流地重复 ListControllers 服务查询，会与官方 spawner 并发。本次仅改项目内探针为被动等待官方 spawner 激活后单次查询，再观察十秒；两次独立启动均通过。系统包、驱动及网络设置完全未变。实施与验证分开见 `diagnostics/FIX.md` 和 `diagnostics/VALIDATION.md`。这些结果支持探针干扰是本次触发条件，但不能声称彻底定位或修复了 Fast DDS 底层 write 失败的全部机制。

上游 [rclcpp 服务响应问题报告](https://github.com/ros2/rclcpp/issues/2760)、[rmw_fastrtps 异常报告](https://github.com/ros2/rmw_fastrtps/issues/706) 仅为相似路径参考，并非采用的修复。没有更换 ROS 版本或中间件；Nav2 端到端与长期稳定性仍不在本次已通过项中。

测试关闭过程中曾需 SIGTERM；仅收尾本任务独立进程组。最终进程检查无匹配的测试 ROS/Gazebo 进程（`logs/post-smoke-processes.log`）。安装日志末尾还有 `OTHER_COMPATIBILITY_COMPONENT_CHANGED_REVIEW_REQUIRED` 标记，标准 APT/dpkg 配置中未定位其来源；安装退出码和包审计正常，标记保留供桌面兼容层后续核对，没有据此擅改设置。

## 数据缺项与启动方式

`src/frontend/public/data` 指向 `data/bpp/exports`，该历史数据目前不存在；前端 inputs/research、后端 packages 的历史数据同样尚未恢复。使用真实资料包恢复后再执行标准构建，不应以空数据或测试夹具替代：

```bash
cd /home/peakpeng/Desktop/URP
python3 tools/restore_materials.py /实际路径/URP.zip --include data/bpp data/packages
bash src/start.sh build
bash src/start.sh frontend
```

前端预览为 `http://127.0.0.1:4173`。后端启动为 `bash src/start.sh backend`，地址 `http://127.0.0.1:4180`，历史记录仍需真实数据导入。科研入口使用 `src/research/.venv/bin/python src/research/scripts/urp.py --help`；可重复执行 `smoke` 微型检查，勿启动正式 replay/训练。

系统安装后，在可访问桌面的本机终端分别启动：

```bash
source /opt/ros/humble/setup.bash
rviz2
# 另一个已 source Humble 的终端：
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:=maze
```

上面 TurtleBot4 命令使用随包提供、无需远程 Fuel 模型的 maze 场景，现已通过两次最小启动验证；其退出仍需 SIGTERM 收尾。默认 warehouse/depot 场景可能下载额外 Fuel 资源，本次未验收。Nav2 端到端导航、长期稳定运行与整套科研系统验收未执行。前端历史数据只读搜索未找到可恢复原始包，详情见 `diagnostics/data-search.json`。

## 回退说明

没有自动删除或清理。回退前先关闭对应服务。

- Node 依赖：将新 `src/frontend/node_modules` 移入一个新的备份路径，再把 `setup/2026-10-15/backups/frontend-node_modules-before` 移回原路径；这样两套依赖都保留。项目 npm 锁文件无需回退。
- 科研环境：本次新建的 `src/research/.venv` 可移入新的备份目录；系统 Python 及原有前后端 Python 环境未替换。uv/npm 下载缓存位于 `setup/2026-10-15/cache/`，保留待用户自行决定。
- 构建与检查产物：额外源码打包和临时 SQLite 在 `runtime/`；标准构建尝试可能留下 `src/frontend/dist`。它们不包含新的科研实验结果。
- 稀疏检出：本次仅展开当前提交中的前后端与研究源码，未更新分支；原稀疏规则见 `sparse-checkout-before.txt`，当前见 `sparse-checkout-after.txt`。回收前先检查这些目录中的新增工作，不直接覆盖索引或移除文件。
- 系统包：本次新增列表在 `apt-new-packages.txt`，没有替换原包。如需回退，先针对该列表生成 `apt-get --simulate remove ...` 计划并审核依赖影响，再由用户决定执行；不要使用无审核的 autoremove、purge 或全系统降级。系统安装前后清单已保留。

安装日志和检查成功仅说明列出的依赖/最小检查结果，不构成整套科研系统验收。
