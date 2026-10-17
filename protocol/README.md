# 基线协议与汇总

- 基线实验协议.md：本轮17配置、53问题、5种子/重复、5秒主协议。
- formal_plan.json：17 配置 × 53 问题 × 5 种子/计时重复的 4505 项冻结计划；原始结果另存 experiments/baselines/cvrp，计划文件本身不代表完成状态。
- distribution_metadata.json：53问题的规模、底本、合同与分布元数据；X12逐项核对原论文表格。E/F/P未知的分布不臆测。
- evidence/：原论文PDF和表11–13渲染截图。
- aggregate.py：读取冻结计划与真实result.json/evaluation.json，输出runs.csv和summary.json；保留未启动及失败分母，提供逐例、分层、算例等权/底本等权和共同有效配对结果。
- test_aggregate.py：合成测试，不是优化实验；覆盖失败/未启动、哈希拒绝、共同配对和底本统计。

用法（在工程根目录）：

    python protocol/aggregate.py --plan <冻结计划.json> --cases src/research/configs/cvrplib_cases.json --distribution protocol/distribution_metadata.json --runs <本次正式结果目录> --out <汇总目录>
    python -m unittest discover -s protocol -p test_aggregate.py -v

测试输出 tests-empty 仅用于验证4505个未启动计划项不会凭空产生有效分数，不得作为正式结果。正式结果目录内同一计划键只允许一个预先指定的分析尝试；全部重试原始文件另行保留，不择优。

## 双主机分工后的汇总

使用 aggregate_hosts.py 替代单主机 aggregate.py 作为交付入口：

    python protocol/aggregate_hosts.py --plan protocol/formal_plan.json --cases src/research/configs/cvrplib_cases.json --distribution protocol/distribution_metadata.json --runs <合并结果根目录> --assignment protocol/ownership_assignment_v3.json --out <分主机汇总目录>

合并时保留 cloud/ 与 ubuntu-local/ 各自的目录、environment.json 和经核验的 host_manifest.json；不要把本机结果塞进云端manifest覆盖的目录。各资源批次可在子目录放更近的manifest。模板在 host_manifest_template.json。结果中的 host_id、machine_id、resource_cohort、resource_batch_id 只作为声明与 manifest 对照；声明或计划分配本身不构成已验证执行证据。旧云端193条通过环境与暂停记录关联，不重写原始结果。

只有最近的 manifest 标记 VERIFIED、与冻结计划匹配、且所指环境文件哈希一致，才设置 host_verified。更近但未核验的 manifest 会阻止继承旧父目录的归属。声明冲突、环境缺失或哈希不符均保留计划分母，主机/资源批次标 unknown，并记录 host_provenance_error；不进入已验证 CPU 均值或同机配对。

报告同时给出计划归属进度、实际主机/资源批次分层结果及异构条件下的描述性合并质量。跨主机或未知资源条件不进行同条件配对，不合并速度排名。assignment_mismatch标示实际主机与分配冲突，需核查，不悄悄更改分配。

## 已归档结果重审

[2026-10-17 全量归档审计与更正说明](audits/20261017/README.md)给出 4505 项终态、4 次仅保留 claim 的中断尝试以及 901/901/2703 项主机证据的不同证明程度。原历史报告和压缩包保持原样，更正单独记录。

下列命令校验原始压缩包摘要，临时解包，独立重算全部路线与 53 份参考解，并输出新审计文件；不启动优化算法，也不覆盖已有输出。

    python independent/audit_archives.py --output /tmp/urp-archive-review.json
    python -m unittest discover -s protocol -p 'test_*.py' -v
    python -m unittest discover -s independent -p 'test_*.py' -v
