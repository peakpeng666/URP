> 本文件保留部署阶段的原始结论；接续集成后的实际状态见 [集成验收报告](../integration/REPORT.md)，使用入口见 [setup/README](../../README.md)。

# Setup 本轮交付与未验收项

记录日期：2026-10-15。项目：`/home/peakpeng/Desktop/URP`。本报告更新上一阶段的安装结论；历史日志保持原样。

**依赖安装完成，前端构建恢复；官方导航闭环与 120 秒图形观察通过，但重复运行稳定性未验收：桥接退出时仍间歇堆损坏。** 系统最终清单相对安装前新增 450 包、0 升级、0 删除，均能对应本任务两次安装清单；`dpkg --audit` 无输出。没有修改系统 Python、驱动、显示、桌面、电源、安全、网络、sudoers 或全局 Conda，没有提交/推送，没有正式 53 算例或付费模型调用。

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

这些是小样本环境选择，不能外推成整套算法性能提升或全局最优。`URP_WORKERS` 只是选择并行入口时的配置提示，未改写冻结的科研实验协议，原串行脚本仍保持串行。仿真默认无图形窗口；需要可视化时显式启用 GUI/RViz。下述验收只覆盖官方小地图、限定时间和固定版本。

## 官方导航验证与本机修复

桌面排查线程解除暂停后恢复了本轮验证。未修改驱动、显示、刷新率、VRR、桌面主题或系统库。官方 TurtleBot4 `maze.sdf` + 匹配地图，规划控制为 Nav2 NavFn + DWB；没有运行 URP 自研算法或正式数据集。

最终配置启用项目内 TF2 修补、GUI 插件生命周期处理和有序桥接关闭。每轮启动独立进程组，记录真实 Gazebo 位姿、动作状态、传感器、两个代价地图及所有退出状态；异常退出或 SIGKILL 会使验收失败。

| 最终运行 | 范围 | 结果 |
|---|---|---|
| `nav-gui-final-11.json` | GUI + RViz，到达、运动中取消、5 秒停车观察 | PASS，正常退出，无残留 |
| `nav-gui-final-12.json` | GUI + RViz，到达、取消、地图外失败、恢复到达、120 秒观察 | PASS，正常退出，无残留 |
| `nav-gui-final-13.json` | 日常入口、到达、取消、30 秒观察 | 未通过：全局地图观测 age 3.334 秒；退出正常，无残留 |
| `nav-gui-qos-14.json` | 可靠/best-effort 地图对照、TF 时间检查、30 秒观察 | 动作和观测通过；一个红外桥接退出 -6，整轮失败，无残留 |

最终产品配置共 4 轮，整体 PASS 2 轮、正常退出 3 轮；不能挑选通过记录宣称重复稳定。恢复后的验证/诊断共 14 轮，历史阶段另有 12 轮，全部记录保留，当前没有运行中的测试。

两分钟观察轮总计 188.14 秒：首次到达 3.961 秒，Gazebo 实际位置误差 0.251 m；取消请求被接受，动作状态 5；地图外目标约 30.912 秒返回 ABORTED（状态 6），随后恢复到达误差 0.137 m。导航和定位生命周期 shutdown 均为 true。

停车观察 120.000 秒对应仿真时间 119.961 秒（约 1.000 实时倍率）；收到 7498 条激光、7437 条里程计、200 次局部地图、50 次全局地图，结束时数据新鲜且速度接近零。停车时 AMCL 位姿和规划路径不持续发布属于该配置正常行为，未将其当作传感器停更。全轮无旧 TF 导航错误、无异常退出、无 SIGKILL、无进程残留。

整张 GPU 的采样峰值 66°C、65% 利用率、2144 MiB 显存、56.84 W，包括桌面及其他 GPU 用户，不能归为 URP 独占消耗。任务进程 RSS 求和峰值约 3.92 GiB，包含共享页重复计数，不是独占 RAM。预算 300 秒，温度停止阈值 85°C；没有极限压力测试。详见 `gui-sustained-summary.json`、原始 `logs/nav-gui-final-12-*.log`。

### 三类问题与处理

1. **TF2 0.25.23 锁顺序死锁。** 无 ROS 节点、DDS 或 GPU 的两线程程序复现锁顺序反转，GDB 确认等待栈。项目候选改为每请求注册锁，不再持有全局定时器映射锁进入请求注册。三次 10 秒 CPU 复现持续更新约六万次并正常结束；立即、延迟、超时与超时后不重复回调语义通过。集成时限定加载到导航、AMCL 定位与 RViz 进程，未替换 `/opt/ros` 文件。仅覆盖导航曾使 AMCL 激活失败，原记录 `nav-candidate-2.json` 保留。
2. **GUI 插件提前卸载。** Gazebo 的无效地址落在已卸载的官方 HMI 插件只读段；RViz GDB 记录显示 Nav2 面板插件先卸载，随后回调组释放弱引用时访问该插件已失效的虚表。项目小型加载器只对三个精确官方插件路径添加 `RTLD_NODELETE`，库映射保留到进程结束，对象仍正常析构。系统插件未改；额外映射随进程退出回收。Qt Fusion/空插件路径对照仍崩溃，故没有归因或修改桌面主题。
3. **桥接同时接收关闭信号。** 组合进程组中断曾间歇使桥接 abort；没有取得本次桥接堆损坏的崩溃栈，不声称已证明底层原因。当前先暂停物理、关闭导航和定位，再通过 pidfd 向本任务桥接子进程发送一次 SIGINT，限定等待后关闭其启动器，曾连续三轮正常，但第 14 轮仍在 `ir_intensity_right_bridge` 退出时报 `free(): corrupted unsorted chunks`、SIGABRT（-6）。因此关闭顺序不是完整修复，桥接根因仍未定位。只关闭本任务创建的进程。

证据：`tf-candidate-validation.json`、`tf-repro/buffer-registration-gate.patch`、`logs/tf-repro-stacks-final.txt`、`gui-shutdown-analysis.json`、`logs/nav-rviz-stack-10-rviz.log`、`gui-plugin-lifetime.cpp`。官方对应源码及 SHA256 在 `upstream/`，例如 [TF Buffer 0.25.23](https://raw.githubusercontent.com/ros2/geometry2/0.25.23/tf2_ros/src/buffer.cpp)、[Gazebo GUI 6.9.0](https://raw.githubusercontent.com/gazebosim/gz-gui/ignition-gui6_6.9.0/src/Application.cc)、[rclcpp 16.0.21](https://raw.githubusercontent.com/ros2/rclcpp/16.0.21/rclcpp/src/rclcpp/callback_group.cpp)。这是本机项目级修复，不是宣称上游已发布修复。

`tf2-overlay-manifest.json` 和 `gui-overlay-manifest.json` 固定系统库、源码和候选二进制指纹；不匹配或缺失时拒绝加载。正向校验和篡改指纹拒绝检查见 `overlay-guard-validation.json`。库升级后要重新构建、核对 ABI 和复测，不能只改指纹绕过保护。

第 14 轮观测到地图发布者为 RELIABLE/TRANSIENT_LOCAL，已让地图探针匹配它并保留原 best-effort 旁路作对照。两路在 30 秒中都收到 17 张全局地图，故没有证明第 13 轮超时来自丢包；原 3 秒阈值未放宽。第 14 轮地图到 base_link 的 TF age 为 0.009 秒。

历史失败与原始 JSON 全部保留。`nav-candidate-gui-4.json` 在旧判定下写了 PASS，但 GUI/RViz 实际退出 -11，**最终归为失败**；历史 `nav-cyclone-ready` / `nav-low-overhead` 也不能忽略强制退出。`nav-debug` 缺扫描重映射，只算隔离诊断。统一解释见 `navigation-summary.json`，不覆盖原记录。

## 启动、范围与剩余项

```bash
cd /home/peakpeng/Desktop/URP
bash setup/run.sh build
bash setup/open-terminal.sh frontend
bash setup/open-terminal.sh backend
bash setup/run.sh research --help
# 无图形窗口的官方导航自动检查
bash setup/run.sh navigation
# 图形 + 失败恢复 + 有预算的持续检查
bash setup/run.sh navigation --gui --rviz --failure-goal --hold 120 --budget 300
```

由于桥接退出缺陷仍在，当前导航入口属于诊断/最小验证入口，尚不应视为稳定实验环境。它会自动脱座、定位、移动、取消并退出；不是人工导航常驻服务。每次有独立日志和 JSON。Ctrl+C 会进入限定清理；运行目录内写入 `STOP` 文件也会停止测试。前端 `http://127.0.0.1:4173`，后端 `http://127.0.0.1:4180`。

尚未验收：长时间任务、复杂地图/动态障碍、真实机器人、手动 RViz/HMI 面板交互及完整科研实验。官方 HMI 仍输出 QML `control is not defined` 等警告，EGL 探测也有警告；实际图形初始化与本轮自动导航通过，但不能把日志检查当作人工视觉验收。用户回复“目前没在看屏幕”，因此**没有肉眼无闪屏结论**。本任务没有修复或宣称修复桌面闪屏。

历史资料仍未恢复。可信归档 `URP.zip` 登记大小 10450371700 字节，SHA256 `9dc81fd8efd41b5c443101dc42773a32454c40fdc56cf8c87f28e821e41b3d38`；本机只读查找未找到，Windows 登记路径不是本机可用文件。拿到原包后执行：

```bash
python3 tools/restore_materials.py /实际路径/URP.zip --include data/bpp data/packages
bash setup/run.sh build
```

下一步优先针对 `ros_gz_bridge` 0.244.26 的红外 LaserScan 桥接做无图形、限定预算的堆损坏复现与带符号/ASan 诊断，保留正常退出断言。项目只读检查发现的系统旧崩溃记录为另一 PID/信号，未把它作为本次 SIGABRT 证据，也未提取其内存。没有继续无边界重跑完整图形测试。

恢复原始资产后再验收真实数据页面；当前缺数据界面与标准构建已处理。最后一次共享重试状态调整后的浏览器复验仍受 IAB 连接限制，构建、测试和本机 HTTP 结果已单独保留。可选 NAS/Torch、外部论文独立环境、正式 53 算例与付费模型均未执行。

## 回退与文件保护

所有默认配置仅作用于项目启动的进程。`URP_TF_FIX=0 bash setup/run.sh navigation` 可停用本地 TF 修补；`URP_GUI_FIX=0` 可停用 GUI 插件生命周期处理。停用会重新暴露上述已知问题，仅用于受控比较。直接使用官方启动命令也不会自动加载这些修补；没有全局 `LD_PRELOAD`。系统库指纹与安装清单保持不变。

前端四个修改文件的原内容在 `baseline/`，回退前先比较后续改动，逐处撤销，不覆盖他人工作。旧 node_modules 在 `../backups/frontend-node_modules-before`；虚拟环境、缓存和日志保留在项目中，没有自动清理。锁文件和原有用户未跟踪文件仅校验哈希，未改写。

若未来要求卸载系统包，先依据 `dpkg-final-diff.json` 的精确新增列表做 APT 模拟，审查连带删除后再操作；不要直接 autoremove/purge 或全系统降级。本轮无权限拒绝、无待输入 sudo；剩余阻碍是尚未修复的桥接堆损坏、来源未明的单次地图观测超时、资料缺失及尚未执行的验收范围。
