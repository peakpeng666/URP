# CVRPLIB 当前入口

更新：2026 年 10 月 19 日。当前材料包括[现用 17 配置基线](baselines/cvrp/README.md)、[冻结计划](../protocol/formal_plan.json)、[基线报告](baselines/cvrp/results/基线实验报告.md)和[归档独立重审](../protocol/audits/20261017/README.md)。不同规模、分布的基础算法对照已有冻结的描述性结果；新研究命题和验收需另行实验与核验。

## 现用结论与分母

| 批次 | 已归档状态 | 统计范围 |
|---|---|---|
| [主 17 配置](baselines/cvrp/README.md) | 17 配置 × 53 问题 × 5 种子 × 每项 5 秒 = 4505 个唯一计划项；4316 有效解、189 无有效解、未启动 0；4509 次尝试含 4 次中断后的原项重试 | 主分母；53 问题对应 51 个底本，容量/车数不同的两对问题分别保留 |
| [vendor 补充](baselines/cvrp/evidence/vendor_all120_audit.json) | AILS-II/SISR，X 集合 12 例 × 5 种子 = 120 项，120 项独立验算有效 | 独立补充批次；主计划仍为 17 配置，而非 19 配置；共享墙钟下的资源效率单独报告 |
| [李月莹验收](baselines/cvrp/handoff/20261016-liyueying/核验与接手.md) | 更早提交 `50b3b2c` 的 5 算法、53 例、5 秒端到端；742/742 复算有效，均为 `acceptance_only` | 算法和种子合同与主计划不同，单独统计；G5 签收不在该批次范围 |
| [16 例旧/新两批](baselines/cvrp/handoff/20261016-liyueying/independent_verification.json) | 1 秒搜索循环，旧 r1 批 48 项逐字节沿用既有记录，新批 48 项；41/48 成本相同 | 共 96 项记录，其中新增 48 项；计时合同与 5 秒端到端批次不同 |

主批次按客户数分为小/中/大规模 41/6/6 例，中大型均来自 X 集合，规模与来源效应存在混杂。分层口径见[算例清单](../src/research/configs/cvrplib_cases.json)和[报告](baselines/cvrp/results/基线实验报告.md)。PyVRP 为 265/265 有效，算例等权参考 gap 约 0.341%；各配置的质量均值与可行覆盖率一并报告。17 配置包含同一算法家族的相近变体。CVRPLIB 的成本与容量合同不含农田障碍、地头、覆盖、车辆动力学或实际执行轨迹。

归档重审将主机/环境证据分为三类：cloud seed0 的 901 项具有已验证包装；cloud seed2 的 901 项具有未 VERIFIED、未链接环境哈希的 host manifest；ubuntu-local seed1/3/4 的 2703 项具有绑定结果 SHA 的 FROZEN resource manifest，缺少原 host/environment 核验包装。各类均保留路线质量记录，其中 901 项支持归档定义的“已验证同条件”统计。速度按硬件分别统计，跨主机波动包含种子与主机的共同影响。分级依据见[审计 JSON](../protocol/audits/20261017/archive_review.json)与[重审说明](../protocol/audits/20261017/README.md)。

## 2026-10-14 运行前验收（历史记录）

2026-10-14 运行前验收通过，VND 来源核验完成；正式实验计划尚未冻结，53 例多种子比较尚未启动。后续主 4505 项、补充批次及重审见上方现用材料。运行前验收与 G5 签收分开记录。

## 运行前验收结果

- 99 项核心回归在最终测试夹具上连续三轮通过，另有主任务第四轮复核；15 项独立故障检查通过。
- 53 项参考解与车队合同验算通过，100 项历史原文件哈希一致，6 份补充参考解来源与验算齐全；53 个问题对应 51 个坐标需求底本。
- 10 次构造小例与 7 次公共算例 smoke 均保存原输出和独立评分，仅用于运行前能力检查。
- PyVRP 原归档/依赖与 VND 原 ZIP 及 10 个成员均完成独立核验。PyVRP 固定 0.14.0，使用 ILS。
- 原始记录保留 98/99 首次失败及夹具前置条件修正，以及旧监督器 24/25 首次失败及未修改源码的复跑。偶发时序风险尚未排除。

## 取用

- [安装与运行](../src/research/docs/CVRPLIB_READINESS.md)：完整 research 基线与新 CVRPLIB 入口在 src/research/，生产源码保持本轮最终验收字节。
- [当前协议](protocols/CVRPLIB_READINESS_PROTOCOL_20261014.md)：输入合同、预算、失败分母与正式冻结边界。
- [独立数据审计](../audits/cvrplib/README.md)：53 例参考解、底本、距离与来源证据。
- [VND 来源核验](../audits/cvrplib/vnd_original/当前核验.md)：原 ZIP、10 个成员、脚本和复核日志。
- [原始验收记录](../acceptance/)：20261014T084727Z 与 20261014T085915Z-test-hardening，包括全部失败记录。
- [输入与参考解](../data/benchmarks/CVRPLIB/)：53 份 VRP、53 份 SOL 及独立的 6 份补充来源说明。
- [离线依赖](../runtime/cvrplib/)：适用于 Linux x86_64、Python 3.12；恢复方式见该目录的复现说明。
- [覆盖清单](../evidence/cvrplib_release/COVERAGE_MANIFEST.json)：本轮文件映射、SHA256、历史保留与依赖恢复映射，范围限于本轮交付。

## 运行前版本与边界

2026-10-14 运行前材料见本页链接；过期说明和重复交付包装可查[历史版本](https://github.com/peakpeng666/URP/tree/ab3a6f4caee7fd961437000fb73c41286f394fd2)。原始成功、失败日志及来源证据保留在 acceptance/、audits/cvrplib/ 和数据目录；两份独有合同审计材料见[独立审查说明](../audits/cvrplib/reviewer/README.md)。历史 253 PASS 和旧研究结论保留原批次归属。

2026-10-14 仅整理归档，未运行新的优化实验、调用生成模型或修改冻结算法。当时用户 Ubuntu 主机尚未实装，全库和前后端不在验收范围。后续正式计划与归档已形成，新的代码或现场验收另行记录。

本页汇总科研批次与历史准入材料；远端提交、云盘核对及清理结果见项目交接索引和完成回执。
