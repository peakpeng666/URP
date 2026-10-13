# 数据

| 目录 | 内容 | 使用方 |
|---|---|---|
| [bpp/inputs](bpp/inputs/) | 装箱原始输入包 | 前端导入与核对 |
| [bpp/records](bpp/records/) | 原始装箱实验记录 | 回放与结果验证 |
| [bpp/exports](bpp/exports/) | 从记录生成的展示数据 | 前端静态页面 |
| [packages](packages/) | selector、budget、fleet、turns、bpp-history记录包 | 科研后端 |
| [benchmarks](benchmarks/) | CVRPLIB、Solomon、Fields2Benchmark农业田形 | 研究输入 |

完整实验包见[实验目录](../experiments/目录.md)。本次从已核验记录重建的后端数据库位于`data/backend/research.sqlite3`，来源见`backend/SOURCE.json`；研究CLI输入位于`data/research/`。

`bpp/exports`是可重建展示，`bpp/records`是原始记录；记录包内的来源附件用于核验。新实验保存输入ID、划分、生成参数和来源哈希。

CIFAR训练数据位于`cifar-training/`，5个原始训练批次的官方来源和摘要见`cifar-training.SOURCE.json`。Solomon保留56份项目原存档输入；CVRPLIB保留53个实例及47份历史参考解，不将历史参考解称作当前最优值。
