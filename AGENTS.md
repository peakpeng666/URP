# URP 工作约定

`main` 是完整集成基线。开始前先看 Git 状态与分支差异，保留本地未提交成果；不要用 reset、强推或批量删除来完成同步。`backup/*` 是历史快照，不应滚动到新版本。

## 入口与分工

- 唯一使用说明：`setup/README.md`；最新现场验收在 `setup/2026-10-15/integration/REPORT.md` 最上方，历史通过不覆盖新改动。
- 农业工作台、算法适配、网关和 ROS 会话：`src/lab/`；前端：`src/frontend/`。
- 档案与有界 CVRP 数值任务：`src/backend/`；研究算法：`src/research/`；独立验算与协议：`independent/`、`protocol/`。
- 首页是科研工作台；`#/jobs` 是数值任务，`#/bpp` 是历史 BPP。保留同一 4100 入口，不重新搭建平行系统。

## 云端环境与检查

云端通常没有 ROS/Gazebo、Fuel 缓存或桌面，不运行依赖本机 ROS 的 `lab-setup` 来准备普通代码任务。从仓库根执行：

```sh
uv sync --locked --extra solvers
npm ci --prefix src/frontend --engine-strict --no-audit --no-fund
uv run --no-sync python tools/check_project.py
```

需要田间 Python 模块时另准备其环境：`cd src/lab && uv sync --locked --inexact`，用该目录 `.venv/bin/python -m pytest -q` 检查。可选 Fields2Cover 及需要本机 ROS/资产的测试应如实报告缺项；不要把云端纯代码检查宣称为真实仿真通过。真实会话测试为 `src/lab/e2e/field_backend.py`，须使用全新绝对输出路径，避免并发运行多个物理验收脚本。

Node 版本与 CI 保持一致（24）；根与 `src/lab` 各有独立 uv 锁文件。勿替换系统 Python 或修改 `/opt/ros`。构建、依赖及大型运行原始数据按 `.gitignore` 不放进 Git 历史；用户授权的完整平台快照作为同仓库 Release 附件发布，入口和校验清单见 `setup/README.md`。恢复必须先校验并解包到新目录，不覆盖现有运行库，也不把环境文件快照当成跨平台安装器。日志摘要、回归脚本与源码应进入 Git。

## 科研结果与数据

- 区分任务访问顺序、米制可行几何路径、实际执行轨迹；未经标定的基准 XY 不能当作米。
- 区分规则推荐与学习模型、URP 路径跟踪与 Nav2 重规划；不得用空值或演示数据补成成功。
- 检查路径段及机器人占用空间，保留随机种子、模型/算法版本、原始结果、失败状态与真实退出码。
- 当前执行为内置同构差速车、串行交通基线。曲率/异构规划通过不代表这些车辆已可物理执行。能耗是版本化后验代理，不是电池实测。
- `data/`、`experiments/`、`protocol/` 的已有证据与历史失败保留；应用可写数据库用 `.local-state/` 和 `src/lab/runtime/`，不要覆盖冻结档案。
- 新说明应更新现有入口及验收报告，不创建多个“最终版”。报告验证范围、未完成项与证据路径。
