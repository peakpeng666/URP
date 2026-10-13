"""Independent postrun audit of archived data. Never invokes policy, runner or selector."""
import resource
resource.setrlimit(resource.RLIMIT_CPU,(60,60))
import pathlib,json,hashlib,collections,csv,math,statistics,datetime,time,os
import numpy as np
H=pathlib.Path('/workspace/scratch/27470b7a9f17/independent_bpp_prefix_selection_20261006')
A=pathlib.Path(__file__).resolve().parent
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_bytes())
def same(a,b,path=''):
    if isinstance(a,dict):
        assert set(a)==set(b),(path,set(a)^set(b))
        for k in a:same(a[k],b[k],path+'/'+str(k))
    elif isinstance(a,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):same(x,y,path+'/'+str(i))
    elif isinstance(a,(int,float)) and not isinstance(a,bool):assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-10),(path,a,b)
    else:assert a==b,(path,a,b)
def feature(prefix,state):
    s=sorted(prefix);used=[v for v in state if v<100]
    def q(t):
        z=499*t;i=int(z);return (s[i]+(s[min(499,i+1)]-s[i])*(z-i))/100
    return [sum(1 for v in prefix if (v-1)//10==i)/500 for i in range(10)]+[statistics.mean(prefix)/100,statistics.pstdev(prefix)/100]+[q(t) for t in (.1,.5,.9)]+[sum(prefix[i+1]>prefix[i] for i in range(499))/499,sum(prefix[i+1]<prefix[i] for i in range(499))/499,(statistics.mean(prefix[-100:])-statistics.mean(prefix[:100]))/100,len(used)/500]+[sum(v//10==i for v in used)/len(used) for i in range(10)]+[statistics.mean(used)/100,statistics.pstdev(used)/100]
assert all(os.environ.get(k)=='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])
start=time.process_time();stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();evidence={}
def record(p):
    evidence[str(p.relative_to(H))]=sha(p.read_bytes());return evidence[str(p.relative_to(H))]
freeze=read(H/'FREEZE.json');assert record(H/'FREEZE.json')=='883780fb58189db4159a0e2c99b4c2db43b4b98a36ade8387b795973b5dc153a'
for p,h in freeze['files'].items():assert record(H/p)==h,p
assert record(H/'src/check_cached.py')=='3fd49705988810cfc528aae9397e979e644dba9245d820893cf62478498564d7'
p=read(H/'PROTOCOL.json');model=read(H/'MODEL.json');mf=read(H/'MODEL_FREEZE.json');check=read(H/'CHECK.json');summ=read(H/'analysis/SUMMARY.json');complete=read(H/'RUN_COMPLETE.json');an=read(H/'ANALYSIS_COMPLETE.json');started=read(H/'RUN_STARTED.json')
assert sha((H/'MODEL.json').read_bytes())==mf['model_sha256'];assert started['freeze_sha256']==evidence['FREEZE.json']
assert complete['status']=='complete' and complete['full_runs']==768 and complete['api_charges']==0 and complete['model_calls']==0
assert check['passed'] and check['full_runs_checked']==768 and check['integer_and_decision_steps']==3840000 and check['selector_decisions_checked']==120 and check['same_prefix_future_invariance_groups']==4
assert not (H/'RUN_FAILURE.json').exists();assert started['numerical_cpu_limit']==600 and started['numerical_soft_cpu_limit']==580
assert all(v=='1' for v in started['single_thread_env'].values())
B=['BF','BF_then_EoH'];raw={};trains=[];expected_rows=[];risk_by_group=collections.defaultdict(list);all_costs=[];runs=steps=selections=0
for meta in p['instances']:
    ident=meta['instance_id'];data=read(H/'inputs'/f'{ident}.json');items=data['items'];methods=B if meta['split']=='train' else B+['published_EoH','SELECTOR'];rr={};zz={};ss={};ff={}
    assert len(items)==5000 and all(type(x)==int and 1<=x<=100 for x in items)
    for method in methods:
        file=H/'raw'/f'{ident}__{method}.json';r=read(file);record(file);rr[method]=r;raw[(ident,method)]=r
        assert r['instance_id']==ident and r['policy']==method and r['status']=='complete' and r['error'] is None and r['steps']==5000
        assert r['items_sha256']==sha(canon(items).encode());archive=H/r['trajectory_file'];assert archive==H/'raw'/f'{ident}__{method}.npz';assert record(archive)==r['trajectory_sha256']
        with np.load(archive,allow_pickle=False) as z:arr={k:z[k] for k in z.files}
        assert set(arr)=={'assignment','pre_remaining','post_remaining','feasible_counts','used_bins_after','remaining'}
        assert all(v.shape==(5000,) and np.issubdtype(v.dtype,np.integer) for v in arr.values())
        z={k:v.tolist() for k,v in arr.items()};zz[method]=arr
        state=[100]*5000;counts=[0]*101;counts[100]=5000;used=0;prestate=None
        for j,(item,target,before,after,feasible,used_record) in enumerate(zip(items,z['assignment'],z['pre_remaining'],z['post_remaining'],z['feasible_counts'],z['used_bins_after'])):
            assert 0<=target<5000 and state[target]==before and before>=item and after==before-item and after>=0
            assert feasible==sum(counts[item:])
            used+=before==100;assert used_record==used
            state[target]=after;counts[before]-=1;counts[after]+=1
            if j==499:prestate=state.copy()
        assert state==z['remaining'] and used==r['used_bins']==sum(v<100 for v in state)
        assert sum(100-v for v in state)==sum(items)
        assert sha(canon(prestate).encode())==r['prefix_remaining_sha256'];ss[method]=prestate
        f=feature(items[:500],prestate);ff[method]=f;same(f,r['prefix_features'],ident+'/'+method+'/features')
        assert r['selector_consumed_count']==500
        for k in ['cpu_loop_seconds','cpu_policy_seconds','cpu_selector_seconds','cpu_instrument_feature_seconds','cpu_total_including_serialization_seconds']:assert math.isfinite(r[k]) and r[k]>=0
        assert r['cpu_total_including_serialization_seconds']>=r['cpu_loop_seconds']
        same(r['cpu_policy_seconds']+r['cpu_selector_seconds']+r['cpu_instrument_feature_seconds'],r['cpu_loop_seconds'])
        all_costs.append({'split':meta['split'],'policy':method,**{k:r[k] for k in ['cpu_loop_seconds','cpu_policy_seconds','cpu_selector_seconds','cpu_instrument_feature_seconds','cpu_total_including_serialization_seconds']}})
        runs+=1;steps+=5000
    assert ss['BF']==ss['BF_then_EoH'];assert np.array_equal(zz['BF']['assignment'][:500],zz['BF_then_EoH']['assignment'][:500])
    if meta['split']=='train':trains.append((ident,ff['BF'],[rr[x]['used_bins'] for x in B]))
    else:
        sel=rr['SELECTOR'];ix=sel['decision']['selected_index'];branch=sel['branch'];assert ix in [0,1] and branch==B[ix]
        assert ss['SELECTOR']==ss['BF']
        for k in zz['SELECTOR']:assert np.array_equal(zz['SELECTOR'][k],zz[branch][k]),(ident,k)
        f=np.array(ff['SELECTOR']);z=(f-np.array(model['mean']))/np.array(model['scale']);dist=((np.array(model['x'])-z)**2).sum(1)
        nn=sorted(range(144),key=lambda j:(dist[j],j))[:5];cost=[sum(model['y'][j][i] for j in nn)/5 for i in range(2)]
        expectedix=model['sbs_index'] if cost[0]==cost[1] else int(cost[1]<cost[0])
        assert ix==expectedix and nn==sel['decision']['neighbors'];same(cost,sel['decision']['predicted_final_bins']);same(dist[nn].tolist(),sel['decision']['squared_distances']);same(ff['SELECTOR'],sel['decision']['features']);selections+=1
        if meta['split']=='risk':risk_by_group[meta['group_id']].append({'prefix':items[:500],'state':ss['BF'],'decision':sel['decision'],'branch':branch})
    bins={k:v['used_bins'] for k,v in rr.items()};oracle=min(bins[x] for x in B);pref='tie' if bins['BF']==bins['BF_then_EoH'] else min(B,key=lambda x:bins[x]);sbs=B[model['sbs_index']]
    row={k:meta[k] for k in ['instance_id','group_id','split','family','replicate','order']};row.update(bins);row.update(SBS=bins[sbs],branch_oracle=oracle,oracle_preferred=pref,SBS_regret=bins[sbs]-oracle)
    if meta['split']!='train':row.update(selected_branch=rr['SELECTOR']['branch'],selector_minus_SBS=bins['SELECTOR']-bins[sbs],selector_regret=bins['SELECTOR']-oracle,full_run_oracle=min(bins['BF'],bins['published_EoH']),selector_minus_full_EoH=bins['SELECTOR']-bins['published_EoH'])
    expected_rows.append(row)
assert runs==768 and steps==3840000 and selections==120
assert len(list((H/'raw').glob('*.json')))==768 and len(list((H/'raw').glob('*.npz')))==768
X=np.array([x[1] for x in trains]);Y=np.array([x[2] for x in trains]);mu=X.mean(0);sd=X.std(0);sd[sd==0]=1
same(mu.tolist(),model['mean']);same(sd.tolist(),model['scale']);same(((X-mu)/sd).tolist(),model['x']);same(Y.tolist(),model['y'])
assert model['k']==5 and len(model['mean'])==31 and int(np.argmin(Y.mean(0)))==model['sbs_index']
assert mf['training_rows']==[x[0] for x in trains] and mf['training_labels']==Y.tolist() and mf['training_sbs']==B[model['sbs_index']] and mf['before_confirmation_execution']
same(mf['training_mean_bins'],Y.mean(0).tolist());same(mf['training_oracle_mean_bins'],Y.min(1).mean())
runlog=[json.loads(l) for l in (H/'RUN.log').read_text().splitlines()];assert len(runlog)==265
assert [x['stage'] for x in runlog]==['train']*144+['fit']+['confirmation']*108+['risk']*12
assert runlog[144]['model_hash']==mf['model_sha256'] and runlog[-1]['completed_runs']==768
checklog=[json.loads(l) for l in (H/'CHECK_CACHED.log').read_text().splitlines()];assert len(checklog)==265 and checklog[-2]['checked_runs']==768 and checklog[-1]==check
for rr in risk_by_group.values():assert len(rr)==3 and rr[0]==rr[1]==rr[2]
mean=lambda vals:sum(vals)/len(vals)
def summary(rr):
    delta=[r['selector_minus_SBS'] for r in rr];head=mean([r['SBS_regret'] for r in rr]);reg=mean([r['selector_regret'] for r in rr])
    return {'n':len(rr),'mean_bins':{a:mean([r[a] for r in rr]) for a in ['BF','BF_then_EoH','published_EoH','SELECTOR','SBS','branch_oracle','full_run_oracle']},'selector_minus_SBS_mean':mean(delta),'SBS_oracle_headroom':head,'selector_oracle_regret':reg,'headroom_recovered_fraction':None if head==0 else (head-reg)/head,'W_T_L_vs_SBS':[sum(d<0 for d in delta),sum(d==0 for d in delta),sum(d>0 for d in delta)],'worst_harm_vs_SBS':max(delta),'best_gain_vs_SBS':-min(delta),'choices':{a:sum(r['selected_branch']==a for r in rr) for a in B},'oracle_preferences':{a:sum(r['oracle_preferred']==a for r in rr) for a in B+['tie']}}
by_split={s:[r for r in expected_rows if r['split']==s] for s in ['train','confirmation','risk']}
def csvcheck(path,expected):
    got=list(csv.DictReader(path.open()));assert len(got)==len(expected)
    for a,b in zip(expected,got):
        assert set(a)==set(b),(path,set(a)^set(b))
        for k,v in a.items():same(v,float(b[k]) if isinstance(v,(int,float)) else b[k],str(path)+'/'+k)
for split,rows in by_split.items():csvcheck(H/'analysis'/f'{split}_per_stream.csv',rows)
conf=summary(by_split['confirmation']);risk=summary(by_split['risk']);familyorder=[]
for fam in p['families']:
    for order in p['orders']:
        ss=summary([r for r in by_split['confirmation'] if r['family']==fam and r['order']==order])
        familyorder.append({'family':fam,'order':order,'n':ss['n'],**ss['mean_bins'],'selector_minus_SBS':ss['selector_minus_SBS_mean'],'SBS_headroom':ss['SBS_oracle_headroom'],'selector_regret':ss['selector_oracle_regret'],'BF_selections':ss['choices']['BF'],'EoH_selections':ss['choices']['BF_then_EoH'],'wins':ss['W_T_L_vs_SBS'][0],'ties':ss['W_T_L_vs_SBS'][1],'losses':ss['W_T_L_vs_SBS'][2]})
csvcheck(H/'analysis/family_order_summary.csv',familyorder)
mat=np.array([[mean([r['selector_minus_SBS'] for r in by_split['confirmation'] if r['family']==fam and r['replicate']==rep]) for rep in range(6)] for fam in p['families']])
seed=int.from_bytes(hashlib.sha256((p['namespace']+'|bootstrap').encode()).digest()[:16],'big');rng=np.random.Generator(np.random.PCG64(seed));indices=rng.integers(0,6,(10000,6,6));boots=mat[np.arange(6)[None,:,None],indices].mean((1,2));ci=np.quantile(boots,[.025,.975]).tolist()
with np.load(H/'analysis/cluster_bootstrap.npz',allow_pickle=False) as z:
    assert np.array_equal(indices,z['indices']);assert np.array_equal(mat,z['group_deltas']);assert np.allclose(boots,z['mean_deltas'],rtol=0,atol=1e-14)
conf['cluster_bootstrap_95_percentile_CI']=ci;same(conf,summ['confirmation']);same(conf,an['primary']);same(risk,summ['risk']['summary'])
groups=[]
for g in sorted(risk_by_group):
    rr=[r for r in by_split['risk'] if r['group_id']==g];prefs=[r['oracle_preferred'] for r in rr]
    groups.append({'group':g,'choice':rr[0]['selected_branch'],'oracle_preferences':prefs,'selector_regrets':[r['selector_regret'] for r in rr],'oracle_preference_reverses':all(b in prefs for b in B)})
same(groups,summ['risk']['groups'])
same({'n':144,'sbs':mf['training_sbs'],'mean_bins':Y.mean(0).tolist(),'branch_oracle_mean':float(Y.min(1).mean()),'SBS_oracle_headroom':mean([r['SBS_regret'] for r in by_split['train']])},summ['training'])
assert summ['bootstrap']['replicates']==10000 and summ['bootstrap']['seed']==seed
same(summ['compute'],{'run':complete,'check':check,'fit_cpu_seconds':mf['fit_cpu_seconds']})
cpurows=[]
for split in ['train','confirmation','risk']:
    for method in B+['published_EoH','SELECTOR']:
        rr=[r for r in all_costs if r['split']==split and r['policy']==method]
        if rr:cpurows.append({'split':split,'policy':method,'runs':len(rr),**{k:sum(r[k] for r in rr) for k in rr[0] if k not in ['split','policy']}})
csvcheck(H/'analysis/cpu_accounting.csv',cpurows)
resources={}
for name,internal,cap in [('RUN',complete['total_cpu_seconds'],600),('CHECK_CACHED',check['cpu_seconds'],240),('ANALYZE',an['cpu_seconds'],40)]:
    v=read(H/f'{name}_PROCESS_RESOURCE.json');assert v['exit_code']==0
    same(v['cpu_user_seconds']+v['cpu_system_seconds'],v['cpu_total_seconds']);assert internal<=v['cpu_total_seconds']<=cap
    resources[name]=v
assert sum(c['cpu_total_including_serialization_seconds'] for c in all_costs)<=resources['RUN']['cpu_total_seconds']
for path in ['MODEL.json','MODEL_FREEZE.json','RUN_STARTED.json','RUN_COMPLETE.json','CHECK.json','ANALYSIS_COMPLETE.json','RUN.log','CHECK.log','CHECK_CACHED.log','RUN_PROCESS_RESOURCE.json','CHECK_CACHED_PROCESS_RESOURCE.json','ANALYZE_PROCESS_RESOURCE.json','evidence/POSTRUN_VALIDATOR_IO_AMENDMENT.json','evidence/PRE_VALIDATOR_RESTART_BUDGET.json']:
    record(H/path)
for path in sorted((H/'analysis').glob('*')):
    if path.is_file():record(path)
for path in sorted((H/'figures').glob('*.png')):record(path)
for path,h in freeze['files'].items():assert sha((H/path).read_bytes())==h
result={'schema':'independent-bpp-prefix-result-audit-v1','created_utc':stamp,'passed_scientific_data_checks':True,'frozen_scientific_files_unchanged':True,'freeze_sha256':evidence['FREEZE.json'],'policy_runs_executed_by_auditor':0,'actual_complete_archived_runs':runs,'independently_integer_replayed_steps':steps,'formal_independent_scalar_argmax_checked_steps':check['integer_and_decision_steps'],'formal_checker_source_sha256':evidence['src/check_cached.py'],'selected_index_branch_links_and_predictions_checked':selections,'full_selected_trajectory_array_matches':120,'independent_training_fit_recomputed':True,'risk_same_prefix_future_invariance_groups':len(risk_by_group),'all_264_stream_csv_rows_recomputed':True,'all_18_family_order_cells_recomputed':True,'bootstrap_draw_indices_matched':10000,'bootstrap_means_and_ci_recomputed':True,'confirmation':conf,'risk':{'summary':risk,'groups':groups},'training':summ['training'],'verified_full_process_resources':resources,'measured_three_completed_processes_cpu_seconds':sum(v['cpu_total_seconds'] for v in resources.values()),'historical_total_900_cpu_compliance':'NOT_ESTABLISHED: earlier preparation/static tasks unmetered; interrupted validator exact cost missing; conservative 240 charge is a bound for that validator alone, 100 setup planning allowance is not a measured or proved bound.','prospective_budget_check':'Auditor hard CPU60 and single-thread imposed; parent reports383.983946 remaining before this audit. No policy rerun.','figure_source_data_check':'Frozen analyze.py uses the independently recomputed overall means,18-cell matrix and12 risk regrets; source data match. Original confirmation PNG visually inspected and Chinese glyphs are missing; rendering repair is a separate outstanding deliverable issue.','internal_audit_cpu_seconds':time.process_time()-start,'auditor_rlimit_cpu':[60,60],'audit_script_sha256':sha(pathlib.Path(__file__).read_bytes())}
(A/'FINAL_MACHINE_CHECKS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(A/'RESULT_EVIDENCE_MANIFEST.json').write_text(json.dumps({'created_utc':stamp,'files':evidence},indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['passed_scientific_data_checks','actual_complete_archived_runs','independently_integer_replayed_steps','selected_index_branch_links_and_predictions_checked','confirmation','risk','internal_audit_cpu_seconds']},ensure_ascii=False,indent=2))
