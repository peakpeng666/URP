# 库房固定路线回放

执行源码固定为3acf840d1a0c16ab1cfcca15744e4ea6609ddb35。原始五任务路线来自既有公开Release，按压缩包及成员文件哈希读取；不重新求解、不改变任务顺序。

本地harness已对齐已审核3acf源码的simulation_execution_v2 / execution_budget_v2协议。所需固定策略回执缺失或不符时必须失败，不能静默回退为墙钟执行。本次只完成本地测试，没有运行ROS/Gazebo或GitHub原生验收，也不构成物理通过证据。

## 执行流程

1. 校验当前源码和历史输入；从固定归档还原61项历史资源文件到不存在的新缓存，核对精确文件与目录集，再作原45项场景资源比较。
2. 调用当前独立检查器与地图检查器，确认路线可行。
3. 在新运行目录创建回放记录和当前执行身份。
4. 通过原有网关，以ground_truth定位和唯一follow_path模式执行，显式请求time_basis=simulation及wall_watchdog_s=5400，不传入budget_s覆盖值。
5. 核验提交和终态的完整固定预算策略、关联身份，以及真实轨迹、五个任务到达情况、实际路径碰撞及正常退出。

工作流仍要求maze job通过后，本阶段才在另一台全新标准Ubuntu 22.04 runner运行。规划器按原公式选择的649.6秒不变，在本协议中明确为模拟时钟预算；既不以历史/本次测得时长替换，也不按RTF自动延长。历史0/5与5/5表示单条路线的任务完成数。

墙钟界限分层设置：生命周期7200秒；启动就绪上限1200秒；执行轮询5400秒看门狗加90秒终态处理。启动前及派发前均要求剩余时间至少覆盖30秒提交与5490秒轮询；迟于轮询截止的响应不能通过。正常会话关闭另有DELETE 180秒和状态确认240秒的独立有限预算，网关退出另限240秒。上层runner的验收阶段为9000秒，覆盖历史Fuel资源还原、网关启动和关闭等开销；安装阶段3600秒不变，warehouse job总上限220分钟。

资源来源独立标为historical_release_exact_bytes_v1，不代表当前Fuel版本，也不等同npm校验。执行前后均重新核对固定字节和完整缓存条目，额外目录或文件、链接及特殊文件不能通过。仅四个已核验两侧字节的Jersey路径允许exact_jersey_alias_bytes_v1映射；raw清单与canonical历史清单分别报告，不混同原始路径相等。

## 结果

输出固定字段的有界数值、枚举、布尔值和哈希摘要。新增execution_protocol明确模拟时钟、原规划预算、5400/7200墙钟边界以及提交/终态策略是否核验；策略缺失、变更或预算与原规划不一致时不能PASS。原有路线、碰撞、任务和清理判据保持不变。实时可行性未测得，不能将此协议与默认墙钟实验混同。

原有physical_budget_origin仍表示源码公式重建来源，新策略回执另行标明API实际返回的策略是否吻合。当前地图绑定YAML及图像字节哈希；历史材料没有记录原地图字节哈希。完整历史输入、运行日志和Fuel模型留在临时目录。

## 本地测试

配置SOURCE、MAPS和HISTORY目录后，从本目录运行：

```sh
PYTHONPATH="$SOURCE/src/lab:$SOURCE/src/research/src" URP_ROS_MAPS="$MAPS" URP_HISTORICAL_JSON="$HISTORY" "$SOURCE/src/lab/.venv/bin/python" -m unittest -v test_recheck test_lifecycle
```

上述测试检查数据、独立校验及模拟的接口生命周期；实际仿真由工作流执行。
