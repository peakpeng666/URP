# URP 本机 Setup

依赖安装、前端缺数据修复与小型性能比较已完成；**导航稳定性尚未验收**。完整结果、证据及回退说明见 [本轮报告](2026-10-15/deployment/REPORT.md)，最初安装记录见 [安装报告](2026-10-15/REPORT.md)。

从项目根目录执行：

```bash
bash setup/run.sh build
bash setup/open-terminal.sh frontend
bash setup/open-terminal.sh backend
bash setup/run.sh research --help
```

前端 `http://127.0.0.1:4173`，后端 `http://127.0.0.1:4180`。打开终端的脚本遵循 PATH 中已配置的 `x-terminal-emulator` 适配器，目前为 Ghostty。直接使用 `bash setup/run.sh frontend` 也可在当前终端启动；Ctrl+C 关闭该服务。

历史实验数据未恢复，页面会显示“无历史数据”。不要把示例数据填入正式数据目录。可信归档恢复命令与校验值见本轮报告。

`profile.sh` 仅设置所启动进程的环境变量：research 提供 12 worker 提示、每进程 BLAS 单线程；numpy 为单进程 12 BLAS 线程；frontend 为 4 Rayon 线程。已有串行科研流程不会因设置 `URP_WORKERS` 自动变成并行实验。配置只基于报告中的小型同输入比较。

导航入口为 `bash setup/run.sh navigation`，会自动执行官方 TurtleBot4 脱座、定位、目标导航和取消检查，然后退出；**不是人工导航常驻服务**。它不运行 URP 科研算法。`--gui` 和持续运行尚未完成最终验证。因桌面闪屏协同排查，当前应暂停运行该入口及所有 GPU/仿真负载，待该限制解除后继续验证。

TF 候选补丁位于 `2026-10-15/deployment/tf-repro/`，仅通过 CPU 复现及小型语义测试，没有替换系统库、没有默认启用。不要把候选库配置为全局 `LD_PRELOAD`。
