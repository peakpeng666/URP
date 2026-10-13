"""Pre-fixed outcome analysis: no tuning or changes to selected policies."""
import pathlib,json,hashlib,csv,time,resource,os
import numpy as np
H=pathlib.Path(__file__).resolve().parents[1]
NS='bpp_prefix_selection_20261006_v1'
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def put(p,x):
    with p.open('x') as f:f.write(canon(x)+'\n')
def writecsv(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    resource.setrlimit(resource.RLIMIT_CPU,(40,40));cpu=time.process_time();wall=time.monotonic()
    p=json.loads((H/'PROTOCOL.json').read_bytes());mf=json.loads((H/'MODEL_FREEZE.json').read_bytes());sbs=mf['training_sbs'];rows=[];costs=[]
    for meta in p['instances']:
        methods=['BF','BF_then_EoH'] if meta['split']=='train' else ['BF','BF_then_EoH','published_EoH','SELECTOR']
        rr={a:json.loads((H/'raw'/f"{meta['instance_id']}__{a}.json").read_bytes()) for a in methods}
        for a,r in rr.items():costs.append({'split':meta['split'],'policy':a,**{k:r[k] for k in ['cpu_loop_seconds','cpu_policy_seconds','cpu_selector_seconds','cpu_instrument_feature_seconds','cpu_total_including_serialization_seconds']}})
        bins={a:r['used_bins'] for a,r in rr.items()};oracle=min(bins['BF'],bins['BF_then_EoH']);preferred='tie' if bins['BF']==bins['BF_then_EoH'] else min(['BF','BF_then_EoH'],key=lambda a:bins[a])
        row={k:meta[k] for k in ['instance_id','group_id','split','family','replicate','order']};row.update(bins);row.update({'SBS':bins[sbs],'branch_oracle':oracle,'oracle_preferred':preferred,'SBS_regret':bins[sbs]-oracle})
        if meta['split']!='train':
            row.update({'selected_branch':rr['SELECTOR']['branch'],'selector_minus_SBS':bins['SELECTOR']-bins[sbs],'selector_regret':bins['SELECTOR']-oracle,'full_run_oracle':min(bins['BF'],bins['published_EoH']),'selector_minus_full_EoH':bins['SELECTOR']-bins['published_EoH']})
        rows.append(row)
    mainrows=[r for r in rows if r['split']=='confirmation'];riskrows=[r for r in rows if r['split']=='risk'];trainrows=[r for r in rows if r['split']=='train']
    for name,rr in [('train',trainrows),('confirmation',mainrows),('risk',riskrows)]:writecsv(H/'analysis'/f'{name}_per_stream.csv',rr)
    def summary(rr):
        delta=np.array([r['selector_minus_SBS'] for r in rr]);headroom=float(np.mean([r['SBS_regret'] for r in rr]));regret=float(np.mean([r['selector_regret'] for r in rr]))
        return {'n':len(rr),'mean_bins':{a:float(np.mean([r[a] for r in rr])) for a in ['BF','BF_then_EoH','published_EoH','SELECTOR','SBS','branch_oracle','full_run_oracle']},'selector_minus_SBS_mean':float(delta.mean()),'SBS_oracle_headroom':headroom,'selector_oracle_regret':regret,'headroom_recovered_fraction':None if headroom==0 else (headroom-regret)/headroom,'W_T_L_vs_SBS':[int(np.sum(delta<0)),int(np.sum(delta==0)),int(np.sum(delta>0))],'worst_harm_vs_SBS':int(delta.max()),'best_gain_vs_SBS':int(-delta.min()),'choices':{a:sum(r['selected_branch']==a for r in rr) for a in ['BF','BF_then_EoH']},'oracle_preferences':{a:sum(r['oracle_preferred']==a for r in rr) for a in ['BF','BF_then_EoH','tie']}}
    overall=summary(mainrows);familyorder=[]
    for f in p['families']:
        for order in p['orders']:
            rr=[r for r in mainrows if r['family']==f and r['order']==order];s=summary(rr)
            familyorder.append({'family':f,'order':order,'n':s['n'],**s['mean_bins'],'selector_minus_SBS':s['selector_minus_SBS_mean'],'SBS_headroom':s['SBS_oracle_headroom'],'selector_regret':s['selector_oracle_regret'],'BF_selections':s['choices']['BF'],'EoH_selections':s['choices']['BF_then_EoH'],'wins':s['W_T_L_vs_SBS'][0],'ties':s['W_T_L_vs_SBS'][1],'losses':s['W_T_L_vs_SBS'][2]})
    writecsv(H/'analysis'/'family_order_summary.csv',familyorder)
    # Cluster resampling, one scalar per multiset after averaging three arrival orders.
    group_deltas=np.array([[np.mean([r['selector_minus_SBS'] for r in mainrows if r['family']==f and r['replicate']==rep]) for rep in range(6)] for f in p['families']])
    bootseed=int.from_bytes(hashlib.sha256((NS+'|bootstrap').encode()).digest()[:16],'big');rng=np.random.Generator(np.random.PCG64(bootseed));indices=rng.integers(0,6,size=(10000,6,6));boots=np.take_along_axis(group_deltas[None,:,:],indices,axis=2).mean((1,2));ci=np.quantile(boots,[.025,.975]).tolist()
    with (H/'analysis'/'cluster_bootstrap.npz').open('xb') as f:np.savez_compressed(f,indices=indices,mean_deltas=boots,group_deltas=group_deltas)
    overall['cluster_bootstrap_95_percentile_CI']=ci
    risks=[]
    for g in sorted(set(r['group_id'] for r in riskrows)):
        rr=[r for r in riskrows if r['group_id']==g];risks.append({'group':g,'choice':rr[0]['selected_branch'],'oracle_preferences':[r['oracle_preferred'] for r in rr],'selector_regrets':[r['selector_regret'] for r in rr],'oracle_preference_reverses':{'BF','BF_then_EoH'}.issubset(set(r['oracle_preferred'] for r in rr))})
    cpurows=[]
    for split in ['train','confirmation','risk']:
        for policy in ['BF','BF_then_EoH','published_EoH','SELECTOR']:
            rr=[r for r in costs if r['split']==split and r['policy']==policy]
            if rr:cpurows.append({'split':split,'policy':policy,'runs':len(rr),**{k:sum(r[k] for r in rr) for k in costs[0] if k not in ['split','policy']}})
    writecsv(H/'analysis'/'cpu_accounting.csv',cpurows)
    result={'confirmation':overall,'training':{'n':144,'sbs':sbs,'mean_bins':mf['training_mean_bins'],'branch_oracle_mean':mf['training_oracle_mean_bins'],'SBS_oracle_headroom':float(np.mean([r['SBS_regret'] for r in trainrows]))},'risk':{'summary':summary(riskrows),'groups':risks},'bootstrap':{'replicates':10000,'seed':bootseed,'unit':'same-multiset 3-order group; resampled within6 fixed families','interpretation':'descriptive uncertainty under this predefined synthetic generator mixture, not general deployment or new-family guarantee'},'compute':{'run':json.loads((H/'RUN_COMPLETE.json').read_bytes()),'check':json.loads((H/'CHECK.json').read_bytes()),'fit_cpu_seconds':mf['fit_cpu_seconds']}}
    put(H/'analysis'/'SUMMARY.json',result)
    # Three concise Chinese figures; use installed fonts and package-local cache only.
    os.environ['MPLCONFIGDIR']=str(H/'.mplconfig');import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams['font.family']='Noto Sans CJK SC';plt.rcParams['axes.unicode_minus']=False
    labels=['全程BF','BF→EoH','全程EoH','前缀选择器','训练SBS','同前缀分支oracle'];keys=['BF','BF_then_EoH','published_EoH','SELECTOR','SBS','branch_oracle']
    fig,ax=plt.subplots(figsize=(10,4.8));values=[overall['mean_bins'][k] for k in keys];ax.bar(labels,values,color=['#65849c','#daa64c','#a593ba','#327a64','#999999','#363d48']);ax.set_ylim(min(values)-4,max(values)+4);ax.set_ylabel('确认集平均最终箱数（越少越好）');ax.set_title('仅看前500项：实际执行的选择收益')
    for i,v in enumerate(values):ax.text(i,v+.15,f'{v:.3f}',ha='center',fontsize=10)
    ax.spines[['right','top']].set_visible(False);fig.tight_layout();fig.savefig(H/'figures'/'confirmation_means.png',dpi=180);plt.close(fig)
    a=np.array([r['selector_minus_SBS'] for r in familyorder]).reshape(6,3);fig,ax=plt.subplots(figsize=(8,5));lim=max(1,float(np.max(np.abs(a))));im=ax.imshow(a,cmap='RdBu_r',vmin=-lim,vmax=lim);ax.set_yticks(range(6),['Weibull','均匀','小尺寸Beta','大尺寸Beta','正态','双峰']);ax.set_xticks(range(3),['随机顺序','升序','降序']);ax.set_title('选择器 − 训练SBS：全部18个分布×顺序单元')
    for i in range(6):
        for j in range(3):ax.text(j,i,f'{a[i,j]:+.2f}',ha='center',va='center',color='white' if abs(a[i,j])>lim*.6 else 'black')
    fig.colorbar(im,ax=ax,label='箱数差，负数表示选择器更好');fig.tight_layout();fig.savefig(H/'figures'/'family_order_deltas.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.8));rr=np.array([r['selector_regret'] for r in riskrows]).reshape(4,3)
    for j,l in enumerate(['随机后缀','升序后缀','降序后缀']):ax.bar(np.arange(4)+(j-1)*.24,rr[:,j],width=.24,label=l)
    ax.set_xticks(range(4),['Weibull前缀','均匀前缀','小尺寸Beta前缀','双峰前缀']);ax.set_ylabel('相对同BF前缀分支oracle的箱数后悔');ax.set_title('前缀相同，未来不同：选择必须保持不变');ax.legend();ax.spines[['right','top']].set_visible(False);fig.tight_layout();fig.savefig(H/'figures'/'same_prefix_risk.png',dpi=180);plt.close(fig)
    put(H/'ANALYSIS_COMPLETE.json',{'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-wall,'primary':overall,'all_cases_included':True})
    print(canon(overall))
if __name__=='__main__':main()
