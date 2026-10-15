#!/usr/bin/env python3
"""Render genuine host-aware aggregate outputs; no synthetic or imputed scores."""
import argparse,csv,hashlib,json,math,os,statistics
from collections import defaultdict
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/urp-matplotlib-report')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
COLORS={'feasible':'#0072B2','failed':'#D55E00','pending':'#C8CCD0','quality':'#009E73'}
LABEL={'savings':'Savings','T':'2-opt','TRS':'VND T-R-S','TSR':'VND T-S-R','pyvrp':'PyVRP ILS','ortools':'OR-Tools','nearest_neighbor':'Nearest neighbor','seeded_sweep':'Seeded sweep','savings_vnd':'Savings VND','multistart_vnd':'Multistart VND','random_cheapest':'LNS random/cheapest','random_regret2':'LNS random/regret-2','worst_cheapest':'LNS worst/cheapest','worst_regret2':'LNS worst/regret-2','ga_random_keys':'GA random keys','pso_random_keys':'PSO random keys','de_random_keys':'DE random keys'}
def num(s):
    if s in ('',None,'None','null'):return None
    v=float(s)
    if not math.isfinite(v):raise ValueError('Nonfinite measured value')
    return v

def setup_style():
    # TTC collections may expose only their first (JP) face to Matplotlib.
    # Register it explicitly; it has complete CJK glyph coverage as a portable fallback.
    for path in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'):
        if Path(path).exists(): font_manager.fontManager.addfont(path)
    families={f.name for f in font_manager.fontManager.ttflist}
    font=next((f for f in ('Noto Sans CJK SC','Noto Serif CJK SC','WenQuanYi Zen Hei','Noto Sans CJK JP') if f in families),'DejaVu Sans')
    plt.rcParams.update({'font.family':font,'font.size':10,'axes.titlesize':11,'axes.labelsize':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':False,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'path','axes.unicode_minus':False,'savefig.dpi':240})
    return font

def render(summary,rows,out,partial=False):
    font=setup_style();overall=summary['groups']['overall']['pooled_quality_descriptive'];algs=[x['algorithm'] for x in overall]
    planned=sum(x['planned'] for x in overall);started=sum(x['started'] for x in overall);feasible=sum(x['feasible'] for x in overall)
    if (started<planned or any(r['status'] in ('CHECKER_MISSING','METADATA_MISMATCH','CHECKER_HASH_MISMATCH') for r in rows)) and not partial:raise ValueError('Incomplete/unverified results; use --allow-partial only for explicitly labelled progress figures')
    out.mkdir(parents=True,exist_ok=True);outputs=[];suffix='（阶段结果，非最终比较）' if partial else ''
    def save(fig,name):
        for ext in ('pdf','svg','png'):
            p=out/f'{name}.{ext}';fig.savefig(p,bbox_inches='tight');outputs.append(str(p))
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,7.7));ys=np.arange(len(algs));left=np.zeros(len(algs))
    for field,color,label in [('feasible',COLORS['feasible'],'独立检查可行'),('failed_started',COLORS['failed'],'已执行但无有效解'),('not_started',COLORS['pending'],'未启动')]:
        vals=np.array([x[field]/x['planned']*100 if x['planned'] else 0 for x in overall]);ax.barh(ys,vals,left=left,color=color,label=label,height=.7);left+=vals
    ax.set_yticks(ys,[LABEL.get(a,a) for a in algs]);ax.invert_yaxis();ax.set_xlim(0,113);ax.set_xticks([0,25,50,75,100]);ax.set_xlabel('占计划运行数（%）');ax.set_title('可行覆盖率与完整分母'+suffix)
    for y,x in zip(ys,overall):ax.text(101,y,f"{x['feasible']}/{x['planned']}",va='center',fontsize=8)
    ax.legend(loc='lower left',bbox_to_anchor=(0,1.02),ncol=3,frameon=False);save(fig,'01_feasible_coverage')
    for axis,levels,title in [('size_stratum',['small','medium','large'],'按客户规模'),('distribution',['R','C','RC','unknown'],'按客户分布')]:
        records=summary['groups'][axis]['pooled_quality_descriptive'];lookup={(x['algorithm'],x['group']):x for x in records}
        fig,axs=plt.subplots(1,len(levels),figsize=(4*len(levels),8.5),sharey=True)
        for ax,level in zip(axs,levels):
            for y,a in enumerate(algs):
                x=lookup.get((a,level));v=x.get('case_equal_gap_percent') if x else None
                if v is not None:
                    ax.barh(y,v,color=COLORS['quality'],height=.65);ax.annotate(f"{v:.2f}%  n={x['quality_case_count']}",(v,y),xytext=(3,0),textcoords='offset points',va='center',fontsize=7)
                else:ax.text(.02,y,'无有效质量数据',transform=ax.get_yaxis_transform(),va='center',fontsize=7,color='#666666')
            ax.set_title(level);ax.axvline(0,color='#777777',linewidth=.7);ax.set_xlabel('算例等权参考 gap（%）');ax.margins(x=.5);ax.grid(axis='x',alpha=.18)
        axs[0].set_yticks(range(len(algs)),[LABEL.get(a,a) for a in algs]);axs[0].invert_yaxis();fig.suptitle(title+'：有效结果的条件质量'+suffix,y=1.01);fig.text(.1,.015,'n为有有效gap的问题数；请同时阅读覆盖率。合并质量为异构主机描述，不是同硬件公平排序。',fontsize=9);save(fig,'02_gap_'+axis)
    # CPU time is separated by actual host/resource cohort, never pooled.
    timing=defaultdict(lambda:defaultdict(list))
    for r in rows:
        host=r.get('host_id','unknown');cohort=r.get('resource_cohort','unknown');v=num(r.get('cpu_seconds'))
        if host!='unknown' and cohort not in ('unknown','not_started') and v is not None:timing[(host,cohort)][r['algorithm']].append(v)
    for index,((host,cohort),vals) in enumerate(sorted(timing.items())):
        fig,ax=plt.subplots(figsize=(10,7.7));present=[a for a in algs if vals[a]]
        if present:
            ax.boxplot([vals[a] for a in present],orientation='horizontal',tick_labels=[LABEL.get(a,a) for a in present],showfliers=False,patch_artist=True,boxprops={'facecolor':'#D6EAF4','edgecolor':'#0072B2'},medianprops={'color':'#D55E00'})
            ax.invert_yaxis()
        ax.set_xlim(left=0);ax.set_xlabel('工作进程 CPU 时间（秒；含初始化及导入）');ax.set_title(f'{host} / {cohort}\n同资源批次时间分布'+suffix);ax.grid(axis='x',alpha=.18);save(fig,f'03_cpu_host_{index+1}')
    # Repeat variability: SD within each problem, not standard error or independent-task uncertainty.
    buckets=defaultdict(list)
    for r in rows:
        v=num(r.get('gap_percent'));h=(r.get('host_id','unknown'),r.get('resource_cohort','unknown'))
        if v is not None and 'unknown' not in h:buckets[(h,r['algorithm'],r['case_id'])].append(v)
    variations=defaultdict(lambda:defaultdict(list))
    for (h,a,c),vals in buckets.items():
        if len(vals)>=2:variations[h][a].append(statistics.stdev(vals))
    for index,(h,vals) in enumerate(sorted(variations.items())):
        fig,ax=plt.subplots(figsize=(10,7.7));present=[a for a in algs if vals[a]]
        ax.barh(range(len(present)),[statistics.median(vals[a]) for a in present],color='#CC79A7');ax.set_yticks(range(len(present)),[LABEL.get(a,a) for a in present]);ax.invert_yaxis();ax.set_xlabel('逐问题重复 gap 标准差的中位数（百分点）');ax.set_title(f'{h[0]} / {h[1]}\n重复波动，不是置信区间'+suffix);save(fig,f'04_repeat_variation_host_{index+1}')
    return {'planned':planned,'started':started,'feasible':feasible,'partial':partial,'font':font,'files':outputs,'notes':['Figures use measured aggregate data only.','No significance or SOTA claims.','Conditional quality must be read with feasibility coverage.']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--summary',required=True,type=Path);p.add_argument('--rows',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--allow-partial',action='store_true');a=p.parse_args()
    s=json.loads(a.summary.read_text());rows=list(csv.DictReader(a.rows.open()));m=render(s,rows,a.out,a.allow_partial);m.update(summary_sha256=hashlib.sha256(a.summary.read_bytes()).hexdigest(),rows_sha256=hashlib.sha256(a.rows.read_bytes()).hexdigest());(a.out/'figure_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
