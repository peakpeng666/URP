# 基线协议与汇总

- 基线实验协议.md：本轮17配置、53问题、5种子/重复、5秒主协议。
- formal_plan_template.json：4505项计划模板；正式运行须另写冻结计划、补齐实际源码/环境哈希并获得启动指令。模板不是已启动证据。
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

合并时保留 cloud/ 与 ubuntu-local/ 各自的目录、environment.json 和经核验的 host_manifest.json；不要把本机结果塞进云端manifest覆盖的目录。各资源批次可在子目录放更近的manifest。模板在 host_manifest_template.json。主机归属支持结果中的host_id或machine_id；旧云端193条通过环境与暂停记录关联，不重写原始结果。

报告同时给出计划归属进度、实际主机/资源批次分层结果及异构条件下的描述性合并质量。跨主机或未知资源条件不进行同条件配对，不合并速度排名。assignment_mismatch标示实际主机与分配冲突，需核查，不悄悄更改分配。
