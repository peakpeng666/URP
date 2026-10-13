# 两批代码核查：精简包交付边界

此说明与 `release_allowlist_v1.json` 是2026-10-05合并后的权威精简交付清单。旧 `delivery_manifest.json` 与 `batch2/validation_and_delivery.json` 保留为各阶段历史记录，不入此精简包；前者记录的旧review_index哈希不再代表当前累计索引。

## 包内

两批中文分析、当前累计论文/笔记索引、两批源码来源清单（只有身份、链接、commit和哈希等元数据）、许可分析及必要许可文本。当前review_index含46条：10条限定源码链已核、2条本批未取得来源；其余未在这两批重新核代码。下载与实际阅读范围分开。

## 包外

所有下载或复用的作者源码正文、数据、模型、运行环境、历史索引快照及阶段校验账本全部外置。即使某仓许可明确，也不默认把源码装入本精简包。

来源清单和review_index中的local_path是原研究工作区的核验位置，不是包内路径；sources、batch2/sources及URP/experiments等引用在本包中不会解析为本地文件。请使用同条记录的固定commit官方url核验。论文阅读笔记路径同为工作区参考，不保证包含在本精简包。

许可正文仅为来源/权利记录，不代表取得额外授权。LLM4AD根许可与部分文件头研究用途/商业联系文字不一致，未宣称可任意复用；EPS未取得统一根许可；CoupleEvo/DGS未取得代码或代码许可。代码许可不自动覆盖数据和模型。

本包没有执行作者程序或数值复现凭证；code_inspected仅适用于明确的read_ranges，executed和numerically_aligned均为false。已有URP实验报告只是外部关联，不能计为作者源码执行。

打包时按release_allowlist_v1.json精确选文件，并另加入该清单自身；不要递归复制整个algorithm_design目录。清单不包含自身哈希，交付校验应使用打包方记录的清单文件SHA256。
