# 官方 CVRP 小型基准包

已从 CVRPLIB 官方现站取得 3 个经典实例及对应官方解，完成纯本地解析、整数距离矩阵构造与解的只读复算。未运行 solver、搜索算法或模型；未安装软件、执行下载代码、登录账号或向外上传。

目录名沿用任务指定的 `20261008` 标签；本次实际抓取时间为 **2026-10-07 UTC**，每个文件的精确时间见 `manifest.json`。

## 立即可用的数据

| 实例 | 总点数（含仓库） | 客户数 | 官网 K | 容量 Q | 总需求 | 官方 UB | 官方 Opt |
|---|---:|---:|---:|---:|---:|---:|---|
| A-n32-k5 | 32 | 31 | 5 | 100 | 410 | 784 | yes |
| B-n31-k5 | 31 | 30 | 5 | 100 | 412 | 672 | yes |
| P-n40-k5 | 40 | 39 | 5 | 140 | 618 | 458 | yes |

- `raw/`：6 个官方 `.vrp` / `.sol`，原字节未改写。
- `clean/*.instance.json`：用于后续算法的纯输入。包含原始坐标、需求、容量、显式整数距离矩阵和 `fixed_k=5`；不包含参考路线。
- `clean/*.reference_solution.json`：官方参考路线及复算结果，仅供验收和评价；不要把这些路线用于算法初始化、父代提示词或搜索。
- `manifest.json`：官方 URL、最终 URL、抓取时间、HTTP 元信息、原字节 SHA-256 与大小、字段含义、版本和许可边界。
- `audit/validation.json`：完整校验结果；`audit/source_table_rows.json` 与 `sources/*.official_table_row.html` 是官网原表的抽取证据。
- `sources/`：本次读取的官网页面与 TSPLIB 原作者文档快照。HTML/PDF 仅作不可信数据存档，没有执行其中内容。
- `prepare_data.py`：本任务编写的离线 stdlib 解析/复核脚本，不是下载的程序，不含网络操作、求解或搜索。

## 官方来源与版本

官方目录：[CVRPLIB All Instances](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/instances)。[About](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/about) 说明了建站作者及现任维护者。目录将本次 A、B、P 三组归于 Augerat et al. (1995)，并直接链接实例和解：

| 实例 | 实例原文件 | 官方解原文件 |
|---|---|---|
| A-n32-k5 | [instance/4](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/download/instance/4) | [bks/4](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/download/bks/4) |
| B-n31-k5 | [instance/6](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/download/instance/6) | [bks/6](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/download/bks/6) |
| P-n40-k5 | [instance/82](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/download/instance/82) | [bks/82](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/download/bks/82) |

链接均由官方目录实际提供，没有猜测路径。官方 HTTP 下载未暴露可固定的版本号或 commit；以记录的 SHA-256 固定本次字节快照。`Last-Modified` 等服务器字段如有，仅当元数据保存，不冒充数据集版本。

## 固定 K 的口径

官网表格独立列出 `|K|=5`，原 `.vrp` 的 COMMENT 也写有 `No of trucks: 5`。这不是仅根据文件名中的 k 推断。

但本次读取的来源没有明确用“至多 5 辆”或“恰好 5 辆”的关系定义该字段；TSPLIB 通用 CVRP 定义甚至不指定车数。因此 `vehicle_upper_bound_explicitly_specified=null`，表示这一强语义**未知**，不能自动宣称官方统一施加车辆上限。

为与后续固定 K 研究对接，本包明确采用**恰好 5 条非空路线**这一局部实验口径。三个实例均有 `ceil(总需求/Q)=5`，且官方参考解均实际使用 5 条合法路线，所以该口径有直接可行性证据。这个协议下“至多 5 条”与“恰好 5 条”由容量下界等价；不能据此推广到别的实例或更宽松车数的实验。

## 距离与索引：必须遵守

三份原文件均为 `EDGE_WEIGHT_TYPE: EUC_2D`。

- [TSPLIB 95 原作者文档](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/tsp95.pdf) §2.1，印刷第 6 页，规定先计算欧氏边长，再应用 `nint`。
- [原作者 FAQ](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/TSPFAQ.html) 定义半整数向绝对值较大的整数舍入。这里边长非负，因此每条边使用 `floor(sqrt(dx²+dy²)+0.5)`；之后才求路线总和。
- 不得使用连续欧氏总长、总长最后统一取整、向上取整或 Python 的 half-to-even `round()` 替代。
- 本包坐标全是整数。矩阵采用 `isqrt` 与整数阈值比较精确实现上述规则，并与文档浮点公式逐点对照，全部一致。
- 原 `.vrp` 使用点号 `1..DIMENSION`，`DEPOT_SECTION` 为 `1, -1`，仓库需求 0。清洁 JSON 使用 `0..DIMENSION-1`，仓库为 0；`node_ids_original` 保存反向映射。
- 本次官方 `.sol` 的客户标号是 `1..客户数`；标号 c 对应原 `.vrp` 点号 c+1，也等于清洁 JSON 的数组下标 c。此映射由全部客户覆盖及三个总成本复现核验，非套用 `.vrp` 原 ID。清洁参考路线不显式列仓库，计价时在首尾补 0。

几何边界：B-n31-k5 存在两对同坐标的不同客户（清洁索引 7/30 与 13/17；原点号 8/31 与 14/18）。需求均应保留，不能去重，也不能假定所有非对角边成本都大于零。逐边整数舍入可破坏三角不等式；本包三组确实都有这种情况，数量见校验 JSON。算法应直接消费显式矩阵，避免借用连续欧氏几何的隐含保证。

## 验证结果与主张边界

逐条确认：所有客户恰好访问一次、没有仓库混入客户路线、路线非空、路线数 5、容量合法、回仓计价完整。

| 实例 | 各路线载荷 | 各路线整数成本 | 合计 |
|---|---|---|---:|
| A-n32-k5 | 98, 72, 44, 98, 98 | 155, 73, 59, 267, 230 | 784 |
| B-n31-k5 | 97, 86, 96, 38, 95 | 107, 112, 110, 189, 154 | 672 |
| P-n40-k5 | 119, 116, 114, 131, 138 | 85, 92, 94, 89, 98 | 458 |

上述合计同时匹配 `.sol` 的 Cost、`.vrp` COMMENT 的 Optimal value 与官网表的 UB。官网对本次三个实例均明确标为 `Opt=yes`；本包据此记录“官方标为最优”，没有独立运行最优性证明，也不把其他 BKS 自动称为已证明最优。

作为误用诊断，同样三份路线若错用连续欧氏长，会分别得到约 787.8083、676.7583、461.7262；这些数字不能用于与本包官方 UB 比较。

离线复现：在本目录执行 `python prepare_data.py`。只会读取本目录快照并重建 clean/manifest/audit；不会下载或求解。不要使用 `python -O`，它会关闭脚本中的断言。

## 许可、来源失败与旧数据边界

[CVRPLIB Terms of Use](https://galgos.inf.puc-rio.br/cvrplib/index.php/en/register/terms) 标注更新于 2025 年 12 月，科研使用允许；第 6 节提示数据再分发可能受具体数据文档的额外条件约束。本次未发现这三个原文件中的明确开放数据许可证，SPDX 记为未知。任何代码许可证都不替代数据许可。本包供现有研究私有保存与使用，不授予公开再分发权。本次没有注册账号、提交解或公开发布；网站条款自身声明使用网站受其约束。

P 的官方解曾在网页抓取工具中出现缓存未命中，随后普通 HTTPS 原址读取成功，保留了 HTTP 200 原字节证据。官网指向 DIMACS 格式规则的旧链接返回 404，没有作为依据或绕过任何限制；距离规范由可用的 TSPLIB 官方文档确认。

这是一套新建、独立、有官方来源链的 CVRP 包。此前“56 客户 Solomon”标签数据的官方身份仍未核实；本包没有认证、覆盖、更名或修改那批旧数据，也不混用其连续欧氏口径。只有 3 个小型实例，适合核验与小规模固定 K 实验，不能据此声称已覆盖广泛真实场景或证明算法普遍优越。
