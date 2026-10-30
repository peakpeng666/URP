# 资产权利与恢复队列

复核基线：`8885ef6cf7aebfa592c112f911cb62f3eaab07f0`，日期2026-10-30。原始文件保留；本页把“待核”拆成具体动作和完成条件。

## 按用途处理

|队列|精确范围|下一动作|完成条件|
|---|---|---|---|
|自有研究证据|`experiments/` 内290个压缩包；`data/backend/research.sqlite3`；`data/bpp/` 数据条目|按实验/批次核生成来源，建立逐包SHA256和恢复对照；先保留失败与原始日志|包内相对路径安全、逐文件对应且独立恢复成功；数据库再核完整性和表行数|
|书目与版本|`papers/` 559 PDF；`literature/教材/`16 PDF|依据 `literature/index.csv` 查作者/出版社对应版本许可，填具体PDF授权，不借代码许可代替|每个拟分发PDF有可追溯许可或只保留书目和官方链接|
|项目报告|`docs/reports/` 已登记的报告与LaTeX候选副本|优先核已有副本，避免再次上传同名不同版本|Git blob对应的SHA256及恢复记录闭合|
|数据与模型|`assets.csv` 中1,543个 `dataset-or-model`，另含 `data/benchmarks/Fields2Benchmark/wkt.zip`|区分自生成结果、第三方数据、模型权重；分别挂生成协议或原数据条款|来源版本、使用/分发范围、署名及派生说明齐全|
|CIFAR训练批次|`data/cifar-training/`，校验表 `data/cifar-training.SOURCE.json`|沿用已有五个SHA256核独立副本，不把训练数据当自有成果|五批共153,650,000字节对应完成且恢复成功|
|第三方源码|`src/repos/`75目录|先按以下许可组处理；实际引用的目录优先|上游版本+使用路径+许可/NOTICE+本地修改可追溯|

每项状态分为 `source-identified`、`terms-identified`、`scope-matched`、`restore-verified`；不同状态互不替代。`assets.csv` 保留原始 `review-required`，本页是工作队列，不批量宣称许可已闭合。

## 已有条款线索的分组

- **非商业条款组**：`src/repos/ACCEL/LICENSE`、`src/repos/PLR/LICENSE`、`src/repos/OptiMUS-v0.1/LICENSE`（现有文本索引CC BY-NC 4.0）；`src/repos/InstanceSpace/LICENSE`（PolyForm Noncommercial 1.0.0）。下一步按实际引用文件核研究使用与发布场景，单独标明用途，不把它们重新标成MIT。官方条款：[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en)、[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)。
- **copyleft范围组**：`src/repos/DACE/LICENSE`、`src/repos/HGS-CARP/LICENSE`、`src/repos/HGS-TDCARP/LICENSE`、`src/repos/algorithm_survival_analysis/LICENSE`、`src/repos/online_as/LICENSE` 的现有索引标签为AGPL；`src/repos/irace/LICENSE.md` 为LGPL线索。下一步读精确版本、嵌套许可及实际集成方式，不凭关键词识别器断言覆盖全部文件。DACE尤其保留20个嵌套许可边界。
- **MIT/Apache/BSD文本组**：其余有根许可目录的逐项路径在 `third-party.csv`。下一步保留版权与NOTICE、核上游SHA和修改，不把“宽松许可线索”当整个依赖树已完成审计。BSD需核具体条款数；模型/数据/图片另查。
- **无根文件组**：以下11项，按不同缺口处理，不归为同一种“无授权”。

## 11项逐目录核对

|目录|已有证据|下一动作与收口标准|
|---|---|---|
|`src/repos/AutoML-Zero`|本地树无根许可；[Google上游BUILD](https://github.com/google-research/google-research/blob/master/automl_zero/BUILD) 明示Apache 2.0线索|核本地快照来源SHA与逐文件头，补对应上级LICENSE/NOTICE的来源记录。上游master线索不直接回填为本地已核许可|
|`src/repos/DR-ALNS`|来源索引记录 `144e48f6912ad9967968561b6b0ce90cedcc14aa` 与 [官方仓库](https://github.com/RobbertReijnen/DR-ALNS)|查该固定版本readme/文件头及单独授权；未找到时保留来源链接并将代码再分发列为待确认，不自行写许可|
|`src/repos/EoH-S`|树内 `code/LICENSE` 存在|先读该blob并判定仅code还是更广；顶层资料分开核。完成＝代码范围与外围资料各有状态|
|`src/repos/JAIR2026-FrugalAS`|无根许可；[官方仓库](https://github.com/stacs-cp/JAIR2026-FrugalAS) 与[大学数据页](https://research-portal.st-andrews.ac.uk/en/datasets/stacs-cp-jair2026-frugalas/) 可定位|核源码版本及Zenodo记录许可；`DATASETS/`各子集readme另建来源，不以归档整体许可替代数据来源|
|`src/repos/QD-LHD`|树内README可定位，根许可未发现|从README核官方来源及固定SHA，再查文件头/上级许可；完成＝匹配到本地内容的许可依据|
|`src/repos/QDAIF`|树内README；[作者项目页](https://qdaif.github.io/) 可定位论文与代码|确认本地快照究竟是项目网页、代码或数据再核各自条款，不把论文许可当代码许可|
|`src/repos/QUBE`|历史算法清单仅列README来源快照，树无根许可|先确认当前目录文件类型与来源，按文档或代码实际内容处理；不把README占位当实现依赖|
|`src/repos/VRPAgent`|树内README和生成启发式来源线索，无根许可|核生成启发式、运行框架、模型输出各自来源与条款；以实际将提取的文件为单位闭合|
|`src/repos/aslib_data`|多个子集readme，无统一根许可|按每个scenario来源/发布者核数据条款；代码ASlibScenario的BSD不能套到数据集合|
|`src/repos/open-source-sisr-routing`|`ctop/cvrp/main/pdptw/top/toptw/vrptw/LICENSE.txt` 共7份；ctop/cvrp/pdptw/top/toptw/vrptw各另有两份lib许可，共19份路径|逐算法子树读原条款，保留cxxopts与json独立许可；完成＝拟提取算法及随附库都有许可记录，不要求凭空增加总root许可|
|`src/repos/typesafe-router`|树内README、package.json，无根许可|核package license字段、官方仓库/版本和文件头；package声明与正式许可文件分别记证据，不能默认为npm默认许可|

树路径已核，但本次稀疏克隆未含上述第三方正文blob。旧提交自动获取曾遇GitHub隧道403，后续已关闭lazy fetch，只做本地树检查。精确补件是拟引用目录的README/源头标识和许可blob，不需要重新拉取全部论文、数据或整个仓库。

## 恢复状态

`copies.json` 已登记6个候选，0个完成恢复。已知论文ZIP本次元数据仍可读且大小匹配，权限只有owner/writer用户条目。下载错误发生在文件引用转云端字节的隧道层；本轮没有再次下载或改共享。先解决这个下载路径，再核ZIP成员是否真的覆盖559篇清单；不能用ZIP存在代替逐篇恢复证明。

根LICENSE由自有成果权利人选择，第三方许可按文件保留。具体发布清单需标注上述条款和范围；[GitHub官方说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) 与 [REUSE规范](https://reuse.software/spec/) 支持以清晰声明管理许可，不能以公开可读推断任意再分发权限。
