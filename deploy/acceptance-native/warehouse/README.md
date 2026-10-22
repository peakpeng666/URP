# 库房固定路线回放

在当前源码94420cf3b703c564134048e1b074406df901bba3下，重新校验并执行历史五任务路线。原始路线来自既有公开Release，按压缩包及成员文件哈希读取；不重新求解、不改变任务顺序。

## 执行流程

1. 校验当前源码、历史输入及45项场景资源。
2. 调用当前独立检查器与地图检查器，确认路线可行。
3. 在新运行目录创建回放记录和当前执行身份。
4. 通过原有网关，以ground_truth定位和follow_path模式执行。
5. 检查真实轨迹、五个任务到达情况、实际路径碰撞及正常退出。

maze job通过后，本阶段在另一台全新标准Ubuntu 22.04 runner运行。整体生命周期预算1800秒；物理预算649.6秒按当前源码公式重建。历史0/5与5/5表示单条路线的任务完成数。

## 结果

输出固定字段的数值、状态与哈希摘要。当前地图绑定YAML及图像字节；历史材料没有记录原地图字节哈希。完整历史输入、运行日志和Fuel模型留在临时目录。

## 本地测试

配置SOURCE、MAPS和HISTORY目录后，从本目录运行：

```sh
PYTHONPATH="$SOURCE/src/lab:$SOURCE/src/research/src" URP_ROS_MAPS="$MAPS" URP_HISTORICAL_JSON="$HISTORY" "$SOURCE/src/lab/.venv/bin/python" -m unittest -v test_recheck test_lifecycle
```

上述测试检查数据、独立校验及模拟的接口生命周期；实际仿真由工作流执行。
