# Setup 实际进展（2026-10-15）

依赖安装已完成：原 443 个系统包加后续 CycloneDDS 7 个包，共 450 个新增，0 升级、0 删除；前端锁定安装和科研独立 Python 3.12 环境已建立。最终前端标准构建通过，Vitest 10 通过、2 个原有跳过，历史数据缺失时明确显示“无历史数据”。

基于实际 Ultra 9 275HX / 62 GiB / RTX 5090 Laptop 配置，三轮微型科研并发、NumPy 和标准前端构建对照已完成，结果摘要一致；项目内 profile/run/open-terminal 入口已保存。没有修改驱动、电源、安全、网络或系统终端设置。

完整官方 Nav2 + TurtleBot4 曾两轮完成到达与取消，但重复运行仍出现 Nav2 内部 TF 时间停更，退出时卡在 global_costmap 清理；不能据此宣布稳定性通过。独立观察器的 TF 与 Gazebo 实际位姿继续更新，已将怀疑范围缩小到 Nav2 内部传感器/TF 处理。GDB 诊断轮因扫描 topic 未重映射而没有相同传感器输入，只能作为隔离对照，不能作为完整导航通过的证据。该轮生命周期清理正常。

已收到父线程关于桌面闪屏并行排查的新限制。所有本任务仿真、RViz、Nav2 和 GDB 子进程均已退出，没有残留；后续 Gazebo/GUI、GPU 负载及持续仿真验证暂停，避免干扰 macOS-Desktop 任务。保留日志和失败记录，只继续前端验证、源码分析及低负载检查。没有权限审批拒绝、没有待输入 sudo。

最新实证：不使用 GPU、DDS 或 ROS 节点的两线程小程序已复现系统 TF2 0.25.23 的锁顺序死锁，并获得 GDB 线程栈。项目内候选修补的三个十秒对照均持续更新约六万次后正常退出；立即/延迟/超时语义检查通过。候选未覆盖系统库、未默认启用，官方 Nav2 集成仍未复测。证据：tf-candidate-validation.json、logs/tf-repro-stacks-final.txt、tf-repro/buffer-registration-gate.patch。

完整交付、启动、回退与未验收项已写入 REPORT.md；上级 setup/README.md 提供日常入口。最终 dpkg 比较确认 450 新增、0 改版、0 删除；锁文件和原有两份用户未跟踪文件哈希保持不变。

暂停解除后的第一轮完整官方导航已 PASS：nav-candidate-1.json，实际到达误差 0.2456 m，取消和 30 秒停车观察通过；导航/定位生命周期 shutdown 均 true，所有进程组只需 SIGINT，无残留、无 SIGKILL。系统 TF 库哈希保持原值，候选仅映射进 Nav2 进程组，AMCL 沿用系统库。当前第二轮（210 秒预算）加入地图外目标失败和失败后再到达验证。

恢复复测补充：nav-candidate-2 暴露未覆盖 AMCL 的相同异步 TF 过滤器问题，原失败保留。覆盖限定扩展到官方 Nav2 导航与定位进程后，nav-candidate-3 全部 PASS：到达约 3.961 秒/实际误差 0.254 m，运动中取消成功，地图外目标 31.031 秒返回 ABORTED，随后再到达误差 0.171 m；实时激光被两个代价地图消费，持续更新，生命周期清理正常，无残留。当前普通 GUI+RViz 轮 nav-candidate-gui-4，300秒运行预算、120秒停车观察、85°C停止阈值；保持显示/驱动/VRR设置不变。

图形退出故障实证：Qt 标准样式隔离仍失败，未归因桌面主题。nav-gui-stack-7 的 Gazebo 无效地址落在先前映射的 libTurtlebot4Hmi.so 只读段；RViz GDB 栈在 CallbackGroup 析构时释放插件创建的弱引用控制块。正在对两个精确插件路径验证进程内 RTLD_NODELETE 生命周期处理，不覆盖系统库、不跳过对象析构。用户回复未在看屏幕，不能记录肉眼无闪屏。

nav-gui-final-11 完整图形短测 PASS：到达、取消、5 秒停车；GUI/RViz/所有 ROS 进程正常清理，无 SIGKILL/段错误/残留。Nav2 RViz 插件卸载后 vtable 地址失效由 GDB + ELF 段偏移确认；项目内三插件生命周期保护与有序桥接关闭已落实。nav-gui-final-12 进行失败目标、恢复导航及 120 秒普通图形观察，预算 300 秒。

阶段汇报：恢复后 13 轮验证/诊断已完成，第 14 轮 nav-gui-qos-14 正在运行（180 秒预算）。脱座、定位、到达、取消、地图外 ABORTED、失败后恢复、120 秒 GUI+RViz 已通过。最新 11/12/13 三轮启停均正常清理无崩溃强杀残留；13 轮因 best-effort 大地图观测 age=3.334 秒未判通过，当前做可靠订阅同轮对照并核对 TF 时间，不放宽原阈值。两分钟轮 GPU 峰值 66°C/65%/2144MiB/56.84W，进程 RSS 求和峰值 4112580KiB。剩余只有当前轮结果、最终文件/进程核对和报告，不扩展压力测试。

收束结果：第 14 轮动作、可靠地图与 TF 新鲜度通过（map/base TF age 0.009s），但一个红外桥接退出 free(): corrupted unsorted chunks / -6。有序关闭不是完整根治。最终产品配置 4 轮整体 PASS 2、正常退出 3；重复稳定性未验收。可靠与 best-effort 同轮都收到 17 张全局地图，不能确认第 13 轮超时原因。没有继续完整图形重跑；所有本任务进程已退出。详细更新见 REPORT.md、navigation-summary.json、STAGE-STATUS.json、processes-final.json。
