# 资料与第三方源码

本清单针对提交 `85a7048b3d2e96d3cd7434dacf7848f213ed7d37` 的完整 Git 树生成，包含稀疏检出未下载的文件。共 559 份论文 PDF、16 份教材 PDF、25 份其他 PDF、290 个实验压缩包、5 个其他压缩包、1 份数据库，以及数据与模型文件。源码整理保留这些原文件，迁移数为 0。

- [assets.csv](assets.csv)：逐文件路径、用途、Git blob 标识、权利核验状态、外部副本与 SHA256 栏位。
- [third-party.csv](third-party.csv)：75 个外部代码目录的根许可证路径、文本类型线索、嵌套许可证数量和处置。
- [inventory.json](inventory.json)：提交、数量和待补许可清单。
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

以下 11 个目录未发现根许可证：AutoML-Zero、DR-ALNS、EoH-S、JAIR2026-FrugalAS、QD-LHD、QDAIF、QUBE、VRPAgent、aslib_data、open-source-sisr-routing、typesafe-router。其中部分有嵌套许可证，详见逐项清单；下次提取代码前先补齐上游提交与授权依据。

PDF 的 `rights_status` 逐项记为 `review-required`。文件名、论文 DOI 或代码许可证不能说明某个 PDF 版本的分发权限；清单未将它们一概判为可分发或不可分发。

## 迁移步骤

1. 核对文件用途、权利和保存位置。私有研究资料使用保留原权限的私有存储。
2. 写入独立副本，核对逐文件 SHA256，再实际下载恢复到新目录。
3. 在索引填入可恢复位置、SHA256 和验证记录；完成后，才在后续提交中移出跟踪。

当前 `external_copy` 与 `external_sha256` 均为空，未向 Drive、Release 或其他存储上传资料。Git blob SHA1 标识现有内容；外部迁移使用 SHA256。历史重写单独处理。

更新索引时输出到新目录：

```sh
python3 tools/index_assets.py --ref HEAD --output .local-state/asset-index
```
