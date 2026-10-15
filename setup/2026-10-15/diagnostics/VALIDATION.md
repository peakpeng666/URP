# 修正后的独立验证结果

修正实施见 `FIX.md`，原始失败证据保留在上一层原文件中。此处仅记录修正之后两次独立启动，不覆盖或重新标记旧失败。

| 运行 | ListControllers 请求数 | 两个控制器 | active 后观察 | 时钟/里程计/激光消息数 | 结果 |
|---|---:|---|---:|---|---|
| passive | 1 | joint_state_broadcaster、diffdrive_controller 均 active | 10.001 秒 | 3695 / 621 / 693 | PASS |
| passive-confirm | 1 | joint_state_broadcaster、diffdrive_controller 均 active | 10.002 秒 | 3812 / 620 / 715 | PASS |

两次都在官方随包 maze 场景中创建机器人，时钟前进；未发送运动目标。运行期间没有原先的服务响应异常，停止之前 launch 仍运行。测试结束由 SIGINT 启动收尾，Gazebo 退出仍需 SIGTERM，最后只对本测试独立进程组清理；最终进程检查没有残留。启动可用性通过与优雅退出问题分别记录，不把 SIGTERM 隐藏为完全正常退出。

证据：`../turtlebot4-passive-smoke.json`、`../turtlebot4-passive-confirm-smoke.json`、对应 `../logs/turtlebot4-*-startup.log`、汇总 `validation-results.json`、最终 `../logs/post-smoke-processes.log`。

这两次最小检查支持当前安装能够激活控制器并持续发布传感器数据，也支持避免原高频探针干扰的修正。它不证明底层 Fast DDS 在任何负载下都不会写失败，不覆盖长期稳定性、移动控制、Nav2 端到端导航、默认 warehouse 在线资产或正式科研实验。

历史数据只读搜索结果在 `data-search.json`：检查的本机常见目录深度五层内没有 URP.zip / BPP ZIP / meta.json；Windows 挂载目录为空；当前 HEAD 的 data 只有 README.md。storage.json 记录资料包在 Windows D 盘，未登记云端文件 ID。没有伪造或导入替代数据。
