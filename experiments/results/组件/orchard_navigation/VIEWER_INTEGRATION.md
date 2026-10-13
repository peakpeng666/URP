# 离线查看器接入说明

交付入口：`results/reporting_v2/viewer_data.json`，schema_version 为 `orchard-navigation/1`。本任务仅生产数据，未修改 URP/web。建议在现有查看器新增独立 orchard_navigation 区段，不复用 routing_runs/CVRP schema。

字段：

- protocol：冻结参数、来源、范围、调用与样本计数
- summary：主结果、失败统计、可达/不可达分母及限制
- maps：12个底图，原始障碍矩形与物理尺度，x向右/y向上
- queries：96组配对起终点，expected_reachable/oracle_steps 来自预批次独立BFS
- runs：960主调用；output.path 为原始路径，validation 为独立验收，cpu_ns/wall_ns 为真实时间
- paired_queries：每查询2算法、5次计时中位数、可达同成本/同路径标志及独立分类标志；不可达的same_optimal_cost为null
- map_summary：12底图分别汇总
- sources：固定数据源路径、字节数与SHA256

建议图层：原始障碍为实色、足迹禁行范围为浅色、起终点标志与A*/Dijkstra路径可单独开关。画面纵坐标须翻转或说明采用y向上；障碍矩形包括x1/y1端格。将中心格路径换算物理坐标时使用(x+0.5,y+0.5)*resolution_m。

请同时展示“12张合成底图 / 96配对查询 / 960主调用 / 192重放”，84可达含12同点任务，12不可达。不可达不是碰撞失败；同成本不同路线不是错误。零长度任务长度、转角均为0，不可达为null。累计转角不能标为已实现的车辆平顺性。不要把5次计时重复当随机种子或5个独立任务。

读取器须验证 schema_version 和输入源哈希；JSON内没有可执行代码。原始结果下载分别用raw.jsonl/raw.csv/replay.jsonl；不得读取qa/application_render或自动索引整个项目目录。当前schema是提供给显式适配器的数据契约，并不意味着旧查看器已经支持它。

请优先使用 reporting_v2，主数据中原始分析仅作为历史证据保留；v2仅纠正不可达的成本语义，原始路径、时间、搜索计数及数值摘要均未变更。v2的verification.json和reporting_revision记录了输入哈希与逐字段投影核验。
