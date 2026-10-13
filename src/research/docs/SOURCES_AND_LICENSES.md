# 来源、依赖与许可边界

## 本项目代码来源

工程代码抽取自2026-10-06三项独立URP机制验证，具体原文件哈希、移植目标和变更在 `source_provenance.json`。原文件没有改写；归档源码仅作为校验材料，恢复后不动态导入。原独立研究实现的许可归属尚未由项目所有者指定，本候选不主动添加MIT、Apache或其他公开许可。

本候选只供项目所有者审核及后续私有工程整理。创建私有仓库、公开发布、向第三方再分发或变更许可不包含在本次本地准备中。公开发布前应由所有者确认自有研究代码及所有依赖材料的授权；算法引用不等于代码复制授权。

## 算法与论文出处

- 父代机制：FunSearch，Mathematical discoveries from program search with large language models，Nature，DOI [10.1038/s41586-023-06924-6](https://www.nature.com/articles/s41586-023-06924-6)。既有冻结记录参考[官方代码](https://github.com/google-deepmind/funsearch)提交 `cc53f274237d7ab05c19df939edbc1f9616a7c19`。本版是独立固定档案组件适配，不包含官方仓库副本。
- CVRP选择：AutoFolio既有P069核验记录，对照[kNN与训练SBS原文](https://ml.informatik.uni-freiburg.de/wp-content/uploads/papers/15-JAIR-Autofolio.pdf)。本版不执行SMAC或AutoFolio。
- CRC：Conformal Risk Control，[arXiv 2208.02814v4](https://arxiv.org/html/2208.02814v4#S1.SS1)，既有P116记录核验第1.1节式4、空集回退及第2.1节假设。本版不复制论文全文。
- 转弯模式：Vidal，DOI [10.1287/opre.2017.1595](https://doi.org/10.1287/opre.2017.1595)，既有P343来源为[作者稿](https://w1.cirrelt.ca/~vidalt/papers/NEARP-Vidal-Revision-WP.pdf)，核验范围为§4.1–4.3、§4.6.2及图4。[HGS-CARP](https://github.com/vidalt/HGS-CARP)提交 `08fde6a5672c3814dca1b4450aa9e5968b1d273a` 仅作官方实现定位，没有在本候选执行或打包。

以上是继承的冻结来源身份，不声称本次工程整理重新阅读全文、重跑官方代码或核实最新版本。教师原材料及论文PDF均不放入Git。

## 软件依赖

- 运行与测试：Python标准库。当前验证 CPython 3.12.14、Linux x86_64；支持目标Python 3.10+，未做全部小版本矩阵。
- 转弯完整重放需要 `signal.SIGPROF`、`setitimer`、`SIGALRM`，因此要求Unix类系统；Windows未支持完整重放。
- 不依赖NumPy、PyVRP、PyTorch、Matplotlib、ReportLab或云端API；历史数据中出现的solver名只作为记录身份。
- 未捆绑第三方软件源码、可执行文件、权重或训练数据。Python及可选源码构建工具的许可由各自发行方提供。

## 权限与敏感信息

Drive链接是已有私有交付来源，不改变访问权限。所有归档输入位于被忽略的 `data/`；源代码包没有密钥、Token、账号配置、原始日志或候选程序文本。只采用显式打包白名单，不能把`.gitignore`本身当作已经完成泄露审查的证明。

## NAS fourth-module provenance

The added twelve frozen Python sources are copied byte-for-byte from the [verified NAS Drive delivery](https://drive.google.com/drive/folders/1REkWhOogD2FtnuG80QDj66soVD3JM5j5), with original paths and SHA-256 values in `configs/nas_fidelity.json`. The dataset is the official CIFAR-10 binary archive, kept outside Git and verified against the historical original P4 manifest. No new license is asserted; no paper PDF, extracted full text, training batch, raw log or checkpoint is bundled with source.
