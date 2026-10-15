# Setup 本轮交付与未验收项

记录日期：2026-10-15。项目：`/home/peakpeng/Desktop/URP`。本报告更新上一阶段的安装结论；历史日志保持原样。

**依赖安装完成，前端标准构建恢复，小型实测配置已提供；官方导航稳定性尚未通过。** 系统最终清单相对安装前新增 450 包、0 升级、0 删除，均能对应本任务两次安装清单；`dpkg --audit` 无输出。没有修改系统 Python、驱动、显示、桌面、电源、安全、网络、sudoers 或全局 Conda，没有提交/推送，没有正式 53 算例或付费模型调用。

## 已交付内容

| 内容 | 实际结果 | 证据 |
|---|---|---|
| 原生机器人依赖 | ROS 2 Humble、RViz2、Gazebo Fortress 6.18.0、Nav2、官方 TurtleBot4、匹配桥接可被发现；原 443 新包，加 CycloneDDS 7 新包 | `../dpkg-diff.json`、`dds/dpkg-diff.json`、`dpkg-final-diff.json`、`dpkg-final.tsv` |
| Python / Node | ROS 使用系统 Python 3.10.12；科研 uv 环境 Python 3.12.13；前端原 Python 3.10 / NumPy 2.2.6 保留；Node 24.14.0 / npm 11.19.1 锁定安装成功 | `../versions-after.json`、上一阶段安装日志 |
| 前后端、科研最小检查 | Python 核心导入、三个微型合成例、后端临时数据库和 HTTP 检查通过 | `../research-smoke.json`、`../backend-smoke.json` |
| 前端修复 | 标准 `npm run build` 成功；Vitest 10 通过、2 个原有跳过；replay-client 检查通过 | `frontend-validation.json`、`logs/frontend-build-final.log`、`logs/frontend-tests-final.log`、`logs/replay-client-tests.log` |
| 文件保护 | npm/Python 锁文件与两份原有未跟踪用户文件哈希未变；仅修改前端相关四个原有文件，新增 helper/test 与 setup 目录 | `preserved-files-final.json`、`git-status-final.txt`、`baseline/` |
| 启动入口 | `setup/run.sh`、`profile.sh`、`open-terminal.sh`；后续可见终端使用已配置 Ghostty 适配器 | 项目内脚本、`dds/logs/`、`../terminal-audit.md` |

当前研究源码没有适用的 PyVRP 安装要求，历史的 PyVRP 0.14 标签不能替代当前锁文件，因此未擅自添加。可选 NAS/Torch 和各外部论文仓库的独立环境没有安装。

前端构建现在只跳过缺失的历史 `public/data` 目标，保留原有符号链接；真实资料恢复后仍正常复制。请求明确接受 JSON，只有 `/data/meta.json` 的 HTTP 404 显示“无历史数据”，网络或内容损坏保持错误信息。缺数据时不展示历史结果、回放或核验通过结论。临时测试夹具没有进入正式数据目录。

此前浏览器五个视图均确认显示“无历史数据”。最后一次调整共享重试状态和未知路由后，构建与测试通过，本机 HTTP `/` 为 200、缺失元数据为 404；IAB 复核却报告连接拒绝，未完成这次最终浏览器重验。这个工具连接限制与原生 HTTP 结果分别记录，不能把缓存页面当作最终 UI 验收。

## 实测配置及适用范围

硬件读取到 Intel Core Ultra 9 275HX、24 逻辑 CPU、约 62 GiB RAM、RTX 5090 Laptop（24463 MiB）、驱动 595.99.02。此前 RViz 能建立 OpenGL 4.6 直接渲染；这不能排除用户后来报告的桌面闪屏。没有据此改驱动或电源。详细原始记录在 `hardware.json`。

以下每项同输入、三轮交错运行，表内为墙钟中位数。没有正式科研数据或模型调用。

| 微型工作负载 | 配置 | 中位秒数 | 决定 |
|---|---|---:|---|
| 单一 3×3 路由夹具，128 任务×16 次 | 1 / 4 / 8 / 12 / 24 worker | 0.735 / 0.217 / 0.144 / 0.124 / 0.126 | 提供 12 worker 提示；24 没有收益 |
| 固定种子 768×768 矩阵，16 次乘法 | 继承默认 / 1 / 4 / 8 / 12 BLAS 线程 | 0.180 / 0.293 / 0.112 / 0.092 / 0.077 | 单进程矩阵配置选 12 线程 |
| 同一前端标准构建 | 默认 / 8 / 4 Rayon 线程 | 2.026 / 2.026 / 2.026 | 选 4，保留 CPU 余量，不声称构建加速 |

证据：`performance.json`、`build-performance.json`、`profile-decisions.json`。科研输出摘要一致，矩阵舍入摘要一致，九次构建产物逐文件一致。默认 BLAS 实际线程数未单独记录；它的波动也更大。科研 RSS 指单进程峰值，不是进程树总量。前端构建峰值约 482 MiB，没有需要扩大 Node 堆的证据。

这些是小样本环境选择，不能外推成整套算法性能提升或全局最优。`URP_WORKERS` 只是选择并行入口时的配置提示，未改写冻结的科研实验协议，原串行脚本仍保持串行。仿真配置暂为实验配置，尚未验收。

## 官方导航结果与问题定位

测试使用官方 `maze.sdf` 及匹配 `turtlebot4_navigation/maps/maze.yaml`，算法为官方 NavFn + DWB，**不是 URP 自研算法**。观察器同时记录独立 Gazebo 实际位姿、AMCL、TF、路径、速度、动作状态和清理进程。

| 运行 | 可支持的结论 |
|---|---|
| `nav-low-overhead.json` | 官方目标到达，实际误差 0.242 m；取消成功，持续停车观察 30 秒；Nav2 清理仍需强制结束 |
| `nav-cyclone-ready.json` | 到达耗时 4.111 秒，实际误差 0.237 m；第二目标规划并运动约 1 秒后取消，状态 5；停车观察 30 秒通过；退出卡住 |
| `nav-ready.json` / `nav-cyclone-stop.json` | 复现内部 TF 时间停更；定位/独立观察 TF 继续更新，导航超过截止时间，未通过 |
| `nav-repeat-1.json` / `nav-tf.json` | FastDDS 启动服务响应失败，AMCL 未完成激活 |
| `nav-cyclone-gui-1.json` | 原组合 GUI/服务器启动未就绪；后来拆分 GUI 启动的改动未完成复测 |
| `nav-debug.json` | 隔离诊断轮生命周期正常清理，但当时没有把代价地图 scan topic 重映射到 `/scan`；不能计入完整导航通过 |

所有试验和失败日志保留；汇总见 `navigation-summary.json`。历史 JSON 中 `PASS` 表示当时动作/观察断言通过，不能忽略 `forced_bounded` 清理字段。最终脚本已将这种情况归类为 `DEGRADED_SHUTDOWN` 并返回失败。只向本任务创建、保留身份的进程组发送信号，限定等待并回收子进程；没有扫描并杀死无关 ROS 进程。

已修正探针过度查询、等待控制器/生命周期激活、dock 状态就绪、资源采样过密等测试问题。CycloneDDS 默认参与者容量不足，项目 XML 调整为 99（官方约 50 个进程需要更多参与者）；只作用于该启动进程。换 DDS 没有消除 TF 停更，因此没有把它宣称为根治。

### CPU 复现与候选修补

在安装的 TF2 0.25.23 上，不使用 ROS 节点、DDS、Gazebo 或 GPU 的两线程程序即可复现死锁：`waitForTransform` 持有定时器映射锁等待请求锁；`setTransform` 的请求回调持有请求锁等待定时器映射锁。基线更新计数停止，正常 join 无法结束，13 秒边界终止；独立 GDB 采集确认两个等待栈。

证据：`tf-repro/main.cpp`、`logs/tf-repro-baseline.log`、`logs/tf-repro-stacks-final.txt`。源码依据为官方 [Buffer 实现](https://raw.githubusercontent.com/ros2/geometry2/0.25.23/tf2_ros/src/buffer.cpp) 和 [BufferCore 实现](https://raw.githubusercontent.com/ros2/geometry2/0.25.23/tf2/src/buffer_core.cpp)，下载及 SHA256 保存在 `upstream/sources.json`。

候选修补用每请求的注册锁保护回调与定时器建立顺序，避免持有全局定时器映射锁进入 `addTransformableRequest`。它位于 `tf-repro/buffer-registration-gate.patch` / `buffer_candidate.cpp`，只在项目内编译成测试库。三个 10 秒复现对照均持续更新约 6 万次并正常退出；立即返回、延迟返回、超时及超时后不重复回调的测试均通过。见 `tf-candidate-validation.json`。

**候选修补没有覆盖系统库，也未加入默认启动。** 这证明所复现的底层死锁可被该候选消除；尚未用它复测官方 Nav2，因此不能断言所有导航故障已经修好。真实 ROS 定时器、完整代价地图清理、连续多目标、失败目标及长时间运行仍需验证。

可在不启用 GPU 的情况下重新构建和复现：

```bash
cd /home/peakpeng/Desktop/URP
source /opt/ros/humble/setup.bash
cmake -S setup/2026-10-15/deployment/tf-repro -B setup/2026-10-15/deployment/runtime/tf-repro -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build setup/2026-10-15/deployment/runtime/tf-repro -j1
timeout -s KILL 13s env LD_PRELOAD="$PWD/setup/2026-10-15/deployment/runtime/tf-repro/liburp_tf_buffer.so" setup/2026-10-15/deployment/runtime/tf-repro/tf-repro
```

## 当前暂停项、数据与后续

收到父线程转述的用户新限制后，已暂停所有仿真、GUI/GPU 和持续负载测试，避免干扰另一个项目的桌面闪屏排查。最后检查没有本任务 Gazebo、Nav2、RViz、GDB 或 TF 复现子进程残留。不是权限拒绝，也没有待输入 sudo。

历史数据只读查找仍未找到可信本地归档。仓库登记的 `URP.zip` 大小为 10450371700 字节，SHA256 为 `9dc81fd8efd41b5c443101dc42773a32454c40fdc56cf8c87f28e821e41b3d38`；登记 Windows 路径不能直接当作本机文件。没有编造、下载替代结果或宣称恢复成功。拿到可信原包后：

```bash
python3 tools/restore_materials.py /实际路径/URP.zip --include data/bpp data/packages
bash setup/run.sh build
bash setup/open-terminal.sh frontend
```

下一步是解除仿真暂停后，将候选修补仅用于隔离 Nav2 进程，重复完整到达/取消/失败目标、三次启停与适度持续观察；确认 TF 新鲜度和优雅清理，再决定是否启用项目配置。GUI 分离方案和 RViz 联动也需要复测。历史资产恢复后再验收真实数据页面。当前不具备整套科研系统验收结论。

## 回退

没有自动删除文件。关闭对应服务后，停用 `setup/profile.sh` / `run.sh` 即可停止应用这些环境变量；登录 shell 和系统配置未修改。候选 TF 库没有默认启用，不使用那条 `env LD_PRELOAD=...` 命令即可停用。

前端四个修改文件的原内容在 `baseline/`。若期间有其他改动，先比较再逐处撤销，不覆盖后续工作；新增 helper/test 可单独移入备份。旧 node_modules 在 `../backups/frontend-node_modules-before`，科研新环境在 `src/research/.venv`，可按最初安装报告移入备份，不需要删除系统 Python。

系统包最终精确新增列表在 `dpkg-final-diff.json`。若用户未来要求卸载，先对该列表做 APT 模拟并审查依赖删除影响；不要直接 `autoremove`、`purge` 或全系统降级。安装日志、失败记录及版本清单均保留。
