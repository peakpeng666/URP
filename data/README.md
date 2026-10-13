# 数据

| 目录 | 内容 | 使用方 |
|---|---|---|
| [bpp/inputs](bpp/inputs/) | 装箱原始输入包 | 前端导入与核对 |
| [bpp/records](bpp/records/) | 原始装箱实验记录 | 回放与结果验证 |
| [bpp/exports](bpp/exports/) | 从记录生成的展示数据 | 前端静态页面 |
| [packages](packages/) | selector、budget、fleet、turns、bpp-history记录包 | 科研后端 |
| [benchmarks](benchmarks/) | CARPLIB、CVRPLIB、Solomon、NEARP、农业田形等算例 | 研究输入 |

完整实验包见[实验目录](../experiments/目录.md)。后端数据库位于`src/backend/backend_data/research.sqlite3`；研究CLI恢复的数据放入`data/research/`，由恢复命令创建。

`bpp/exports`是可重建展示，`bpp/records`是原始记录；记录包内的来源附件用于核验。新实验保存输入ID、划分、生成参数和来源哈希。
