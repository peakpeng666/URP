# 原生仿真验收

在GitHub标准Ubuntu 22.04 runner上安装项目环境，运行无界面Gazebo与Nav2，并检查真实轨迹、任务完成和进程清理。首阶段为maze-inspection，使用ground_truth定位和follow_path执行。

## 版本与环境

- 执行源码固定为94420cf3b703c564134048e1b074406df901bba3。
- 验收工具使用另一固定提交；工作流分别检出两个完整SHA。
- 安装调用项目既有workbench流程，并跳过可选Fields2Cover组件。
- HOME、Python环境、运行库和实验输出位于本次runner临时目录；使用Xvfb软件渲染。
- 新建检出目录先还原Git属性声明的换行转换，再逐字节校验原始Git blob；安装前后均验证源码内容。

## 通过条件

完整执行流程成功，真实轨迹有运动，全部任务点到达，规划与实际路径均通过地图检查，源码与原生运行库身份一致，会话及网关正常退出，最终没有自有残留进程。取消、超时或强制清理均按失败记录。

整体实验墙钟预算为1800秒；控制器自己的物理执行预算独立记录，缺失时保留null。接驳仍按项目契约交由Nav2规划。

## 文件与接口

- runner/run.py：安装、Xvfb、验收与清理。
- acceptance.py：调用现有full_loop.py，汇总真实执行证据。
- public_summary.py：生成字段受限的公开摘要。
- runner/verify_worktree.py：校验源码。
- runner/verify_registry.py：将镜像包完整性与官方npm元数据对照。

```sh
python acceptance.py --source SOURCE --private-dir NEW_DIRECTORY --summary SUMMARY --harness-sha COMMIT --stage maze
python public_summary.py --input SUMMARY --runner-status RUNNER_STATUS
python -m unittest -v test_acceptance runner.test_runner runner.test_worktree runner.test_materialize runner.test_apt_diagnostic runner.test_apt_projection runner.test_registry
```

公开摘要包含固定状态、数值、布尔值和摘要哈希；缺测值标null。安装失败时列出经软件包缓存核对的依赖诊断，并标注核验方式。完整日志与运行数据留在临时目录，不上传artifact或缓存。工作流不发布镜像，不修改部署分支，不使用付费runner。

库房固定路线复验为后续阶段，当前工具明确标为NOT_RUN。它需要保留历史五任务几何与精确起点，在新版本下重新校验和生成执行身份。
