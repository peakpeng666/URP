# 2026-10-17 仿真接口与验收修复记录

基准：`50b3b2c2cc7377e1f13dcaeebce09abf5619dbf8`。本目录新增记录；其他 evidence 和历史 PASS/失败记录未修改。

## 真实执行范围

- 基准原有 29 项纯 Python 检查通过，继续补充负向样例。
- 本轮 56 项标准库检查通过，包括实际回调代码的消息替身测试；替身未调用 ROS 通信或 Gazebo。
- `baseline_gaps.json` 通过原提交的 scene/control 源码、抽出的时间戳判断方法和 runner 最终决策块，实际复现了 7 类缺陷并记录修正行为。原 runner 决策块在控制器退出 0、报告缺失时写出 success=false，却仍返回 0；当前报告闸门返回 1。
- `adversarial_initial.log` 保留扩展检查的初次失败：深层 JSON 没有统一深度上限，以及纳秒浮点值采用了不合适的精确相等断言。前者已增加 64 层限制，后者改为容差断言。后续通过结果独立保存。
- Python 编译、shell 语法、合成 route-scene 的离线检查均执行。最终源码摘要及命令结果见本目录的机器可读记录。
- 离线 setuptools wheel 构建通过，确认新增 Python 模块、官方 launch 和版本清单包含在包内，且排除编译产生的 `__pycache__` 目录。构建日志及检查结果单独保存；没有执行 colcon/ROS 构建。

## 没有执行的部分

`upstream_preflight/preflight.json` 是实际运行依赖预检的输出：Ubuntu 24.04，无 ROS Humble、ros2、ign、ament、图形会话；退出 2。

`synthetic_preflight/preflight.json` 是实际运行旧 fixture runner 后得到的缺 Humble 结果；退出 2。

两者均 `runtime_executed=false`。本次没有 ROS 包构建、RViz GUI、libsdformat CLI、Gazebo 插件加载、机器人运动、上游世界装载或真实导航任务验收。纯 Python/XML/消息替身通过不能抵充这些门槛。TurtleBot 4 的 Fuel 资产和完整依赖尚未冻结，且未实现 URP 导航任务执行器。
