# 进程监督

`supervise.py`提供Linux独立进程中的子进程监督、超时清理、`wait4`资源统计和退出记录，供研究执行器集成。

以下命令从URP根目录进入本组件后执行；此处列出命令不表示本轮已执行。

```sh
cd src/research/execution
python3 -m unittest discover -s tests -p 'test_*.py'
```

子进程须留在其独立session/进程组内。实时CPU检查针对主进程，回收后汇总子进程资源；任意代码沙箱及整个进程树的实时CPU限额需由执行环境提供。

测试中的旧监督器仅作为回归反例，位于`tests/fixtures/original_supervise.py`。当前实现为本目录的`supervise.py`。
