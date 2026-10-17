#!/usr/bin/env python3
"""Create concise Chinese factual report from host-aware measured aggregates."""
import argparse,hashlib,json
from pathlib import Path

def fmt(x):return '—' if x is None else f'{x:.3f}'
def main():
 p=argparse.ArgumentParser();p.add_argument('--summary',required=True,type=Path);p.add_argument('--plan',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--allow-partial',action='store_true');p.add_argument('--infrastructure-retries',type=int,default=0);a=p.parse_args();s=json.loads(a.summary.read_text());plan=json.loads(a.plan.read_text());overall=s['groups']['overall']['pooled_quality_descriptive'];n=sum(x['planned'] for x in overall);started=sum(x['started'] for x in overall);feasible=sum(x['feasible'] for x in overall)
 if started<n and not a.allow_partial:raise ValueError('Incomplete matrix; no final report before all planned keys accounted for')
 title='CVRPLIB 基线实验阶段报告' if a.allow_partial else 'CVRPLIB 基线实验报告'
 lines=[f'# {title}','',f"本轮包含{len(plan['algorithms'])}个算法配置、{len(plan['case_ids'])}个问题、51个坐标需求底本，每配置每问题安排{len(plan['seeds'])}次种子/计时重复，每次{plan['budget_seconds']}秒。",'',f'计划{n}项，已启动{started}项，独立验算可行{feasible}项，已启动但无有效解{started-feasible}项，未启动{n-started}项。','', '## 可行性与质量','', '| 算法配置 | 可行/计划 | 有质量数据的问题/底本 | 算例等权参考gap % | 底本等权参考gap % |','|---|---:|---:|---:|---:|']
 if a.infrastructure_retries:
  lines.insert(6,f'执行记录共{started+a.infrastructure_retries}次尝试，对应{started}个唯一计划项。本机有{a.infrastructure_retries}次基础设施中断，各原计划项重试一次；中断记录保留，不作为额外样本或静默丢弃。\n')
 for r in overall:lines.append(f"| {r['algorithm']} | {r['feasible']}/{r['planned']} | {r['quality_case_count']}/{r['quality_base_count']} | {fmt(r['case_equal_gap_percent'])} | {fmt(r['base_equal_gap_percent'])} |")
 lines+=['','质量均值仅针对有效结果，必须与可行覆盖率一起阅读。参考gap以冻结且验算合格的参考解为分母，不将全部参考值称为已证明最优值。53问题中两个容量变体对共享底本；同时报告算例等权与底本等权结果。','','## 规模、分布与执行条件','','小、中、大规模按客户数划分，共41、6、6例。中、大规模均来自X集合，小规模来自A/B/E/F/P，规模与来源效应不能完全分离。X中型随机/聚类/混合各2例；大型分别1/2/3例。对应表图见02_gap_size_stratum和02_gap_distribution。','','云端seed 0/2（1802项）、本机seed 1/3/4（2703项）；按实际主机与资源批次单独报告时间和质量。合并质量是异构执行条件下的描述，不进行跨主机速度排名。算法配对要求同主机、资源批次、问题与种子。云端seed0串行、seed2四核并行是不同资源批次，各只有一次运行，不计算各自的问题内重复标准差。本机原始记录划为4个资源批次，未强行合并；仅b01批次存在同问题的重复，可计算问题内标准差，其他批次不计算。确定性算法重复反映截断和环境波动，重复标准差不是独立问题数或置信区间。','','## 算法来源与农业联系','','GA/PSO/DE随机键+Split为本轮标准教学适配，不冒称历史CVRP复现。其他配置的来源、固定版本和距离适配见算法清单。17个配置不等于17个独立算法家族。','','R/C/RC分布可作为分散服务点、集中收集点、混合区域服务的抽象起点，属于待验证映射，不是农田实测。实验尚不包含作物行、地头转弯、障碍、坡度或覆盖约束，不能据此声称已验证农业机器人导航。分布标签来源：[Uchoa等原论文表11–13](https://optimization-online.org/wp-content/uploads/2014/10/4597.pdf)。','','## 复现','','- 固定计划SHA256：'+hashlib.sha256(a.plan.read_bytes()).hexdigest(),'- 求解器源码SHA256：'+str(plan['solver_source_sha256']),'- 汇总输入SHA256：'+hashlib.sha256(a.summary.read_bytes()).hexdigest(),'- 原始逐项结果、独立验算、失败记录和未启动项均保留；图表由plot_baselines.py读取同一汇总与CSV生成。','']
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text('\n'.join(lines))
if __name__=='__main__':main()
