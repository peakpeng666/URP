# 源码

| 目录 | 当前内容 |
|---|---|
| [research](research/README.md) | 父代选择、CVRP选择与CRC、转弯mode及NAS研究CLI；生成执行组件 |
| [backend](backend/README.md) | 本地实验包导入、SQLite记录、附件、比较和路线API |
| [frontend](frontend/README.md) | BPP结果、回放、选择解释与证据面板；路线组件 |
| [repos](repos/README.md) | 75个外部论文代码目录及来源清单 |

从URP根目录运行：

```sh
bash src/start.sh build
bash src/start.sh frontend       # 127.0.0.1:4173
bash src/start.sh backend        # 127.0.0.1:4180
```

数据位于[../data](../data/README.md)。前端的`inputs`、`research`、`public/data`和后端的`packages`通过相对链接访问同一份数据。Python环境与Node依赖由对应项目维护。

[下一阶段](../下一阶段.md) · [检查记录](checks.json) · [来源记录](sources.json)。
