# 资料与第三方源码

资产目录覆盖 **2,439 个文件、75 个第三方源码目录**。2026-10-30 对照 `8885ef6cf7aebfa592c112f911cb62f3eaab07f0` 完整 Git 树，2,439 个资产路径和 blob 标识全部匹配，无缺项或变更。原清单生成提交为 `85a7048b3d2e96d3cd7434dacf7848f213ed7d37`，其历史信息保留在 `inventory.json`；本次复核见 [review.json](review.json)。树中存在与本地已下载分开记录。

共 559 份论文 PDF、16 份教材 PDF、25 份其他 PDF、290 个实验压缩包、5 个其他压缩包、1 份数据库、1,543 个数据或模型文件。先保持归档完整，再按下面的具体队列处理；当前已验证外部副本与迁移数均为 **0**。

- [assets.csv](assets.csv)：逐文件路径、用途、Git blob 标识、权利核验状态、外部副本与 SHA256 栏位。
- [third-party.csv](third-party.csv)：75 个外部代码目录的根许可证路径、文本类型线索、嵌套许可证数量和处置。
- [inventory.json](inventory.json)：提交、数量和待补许可清单。
- [copies.json](copies.json)：实际副本、权限、上传与恢复状态；只有 `restore-verified` 记录进入已验证副本字段。
- [rights-review.md](rights-review.md)：按许可范围分组的提取与发布队列，以及11个无根许可目录的逐项处理。
- [文献目录](../../literature/index.csv)、[外部仓库来源](../../src/repos/REPOSITORIES.md)、[既有存储说明](../../storage.json)：对应书目、代码来源和历史存储位置。

## 文件分工

| 内容 | 工程中的位置 | 处理方式 |
|---|---|---|
| 源码、配置、小型用例和接口 | `src/`、`tools/`、`setup/`、`deploy/` | 日常开发与回归 |
| 冻结协议、统计表、摘要和失败 | `protocol/`、`experiments/baselines/`、`experiments/reports/` | 保留原版本；新实验另建记录 |
| 压缩结果、数据集与历史数据库 | 见 `assets.csv` | 保留原路径，先建立可验证副本再迁移 |
| 论文与教材 | `papers/`、`literature/教材/` | 逐项核对版本、来源和分发授权，优先维护书目与原文链接 |
| 外部源码 | `src/repos/` | 保留许可证；运行环境用已锁定依赖，后续按实际引用提取补丁与下载清单 |
| 新运行、缓存与依赖 | `.local-state/`、`src/lab/runtime/`、虚拟环境 | 本地写入，定点忽略 |

## 许可核验

仓库尚无根 LICENSE，本轮未代选。第三方文本仍各自适用；`third-party.csv` 的类型来自文件文本识别。

已确认的具体条款线索：`src/repos/ACCEL/LICENSE`、`src/repos/PLR/LICENSE`、`src/repos/OptiMUS-v0.1/LICENSE` 为 CC BY-NC 4.0；`src/repos/InstanceSpace/LICENSE` 为 PolyForm Noncommercial 1.0.0。HGS-CARP、HGS-TDCARP 等目录有 GPL 文本，版本和覆盖范围见其原文件。

11个目录未发现根许可证，已逐项拆入 [rights-review.md](rights-review.md)。其中 EoH-S 的 `code/LICENSE` 和 SISR 的7个算法子目录许可需要按其覆盖范围处理，不把“无根许可”写成“全部无许可”。SISR另有12个 `lib/cxxopts_LICENSE.txt` / `lib/json_LICENSE.txt`，原索引仅按文件名以LICENSE等开头计数，未计入这12份后缀型许可。

PDF 的 `rights_status` 逐项记为 `review-required`。文件名、论文 DOI 或代码许可证不能说明某个 PDF 版本的分发权限；清单未将它们一概判为可分发或不可分发。

## 迁移步骤

1. 核对文件用途、权利和保存位置。私有研究资料使用保留原权限的私有存储。
2. 写入独立副本，核对逐文件 SHA256，再实际下载恢复到新目录。
3. 在索引填入可恢复位置、SHA256 和验证记录；完成后，才在后续提交中移出跟踪。

当前已验证的 `external_copy` 与 `external_sha256` 均为空；本轮上传与候选状态见下节。Git blob SHA1 标识现有内容，外部迁移使用 SHA256。历史重写单独处理。

## 第二轮副本核验

已检查用户指定的私有「实验项目」文件夹，并创建 [URP工程整理-20261030](https://drive.google.com/drive/folders/1RT2EE4UOE5qrbrSizstQDqfroMRwqKmo)。目录权限沿用 owner / writer 两个用户条目，没有公开或域条目，权限未更改。已上传一份 826 字节的资产基线 JSON，文件名、大小、父目录和权限已读回确认；原始内容尚未完成下载恢复校验。

原文件夹中另发现 19,629,355 字节的 `URP-private-papers-20261023.zip` 和四份研究报告 / LaTeX 包。读取该 ZIP 的完整文件引用成功，但云端下载返回 `URLError: Tunnel connection failed: 403 Forbidden`；未恢复文件，也未核对 ZIP 成员。因此本轮大文件迁移和移出跟踪均为 **0**。

| 类别 | 当前方案 | 本轮处置 |
|---|---|---|
| 559 份论文、16 份教材 | 私有保存并逐文件核对来源、版本和权限 | 现有私有 papers ZIP 未核对成员，保留原件 |
| 290 个实验压缩包 | 按实验包保存 SHA256、报告与恢复位置，先校验内部路径再解包 | 现有 Drive 证据包不自动视为同一批次；未移出 |
| BPP 输入与 NPZ 记录 | 作为只读回归数据保存，支持恢复后运行原验算 | 完整保留，源码检出清单继续包含必需 NPZ |
| CIFAR 五个训练批次 | 以 `data/cifar-training.SOURCE.json` 的五个 SHA256 核对独立副本 | 共 153,650,000 字节，未上传或移出 |
| 历史 SQLite | 独立副本恢复后检查字节与 SQLite 完整性、行数 | 本轮未上传数据库，保持只读档案 |
| 项目报告 / LaTeX | 优先核对已有的四份 Drive 文件，避免重复上传 | 已登记候选，尚未逐字节验证 |
| 第三方源码与原生资产 | 按上游提交、许可、补丁和现有平台清单分别恢复 | 保留当前来源与许可证，不打包未知授权资料到公开发布 |

2026-10-30 本次补核已知 papers ZIP 的元数据：文件仍为19,629,355字节，返回 owner / writer 两个用户权限，无公开或域权限条目。元数据读取成功与原下载隧道403是两个独立状态。本次未重复下载；下一步只需在获准且可访问该文件引用的下载环境恢复这一份 ZIP，核 SHA256、成员路径及成员对照后再决定是否覆盖论文清单。无需为此更改共享权限。恢复前其状态保持 `restore-blocked`。

分支状态由 [当前工程索引](../current-index.md) 统一维护；这里仅维护资产身份、权利和恢复状态。

更新索引时输出到新目录：

```sh
python3 tools/index_assets.py --ref HEAD --output .local-state/asset-index
```

重新生成时会读取 `copies.json`：未恢复副本保持候选状态，已验证副本必须包含 URL、Git blob、SHA256 和恢复记录，且 Git blob 与所索引版本一致。
