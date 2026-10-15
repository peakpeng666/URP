# 基线报告与表图

真实数据入口为 protocol/aggregate_hosts.py 输出的 summary.json 和 runs.csv。

    .venv/bin/python reports/plot_baselines.py --summary <summary.json> --rows <runs.csv> --out <图表目录>
    .venv/bin/python reports/build_report.py --summary <summary.json> --plan protocol/formal_plan.json --out <基线实验报告.md>

未完成时默认拒绝生成最终报告。确需阶段快照时加 --allow-partial，标题会明确标为阶段结果。不得将空计划测试、烟测或合成验收数据用于最终图表。文件名不代表实验已完成。

图表以PDF、SVG、PNG三种格式输出，包含完整分母的可行覆盖、按规模/分布的条件质量、分主机资源批次CPU时间、逐问题重复标准差中位数。后者不是置信区间。保留原算法顺序，不通过幸存样本均值制造排行榜。字体优先Noto CJK，图表清单记录实际字体和输入哈希。

时间图只在同主机和固定资源批次内显示；无主机/资源证据的数据不纳入时间图。合并质量是异构条件描述，配合分主机汇总阅读。未知分布保留unknown，不强行归类。

templates/基线报告模板.md提供人工复核结构；最终结论仍须结合真实完成情况与独立验算，不能预写显著性或最先进结论。

当前v3分工为云端seed0/2、本机seed1/3/4；云端串行与四核并行分属不同资源批次，各仅一次运行；本机相同资源配置时最多3次重复。主机归属以ownership_assignment_v3.json和实际记录为准。
