"""One-shot bounded fixed grid; adapted from paper_design_panel_v1/run_once.py.
No dynamic program execution. CLI requires explicit freeze-bound approval file.
"""
import hashlib,json,os,pathlib,resource,signal,subprocess,sys,time,warnings
P=pathlib.Path(__file__).resolve().parent; B=P.parent
FREEZE=P/'execution_freeze.json'; OUT=P/'run'
SCOPE='eoh_parameter_control_27_design_then_5_test_v1'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    with p.open('x') as f:
        json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False); f.flush();os.fsync(f.fileno())

def verify():
    f=json.loads(FREEZE.read_text())
    for name,sha in f['files'].items():
        if digest(B/name)!=sha:raise ValueError('frozen file mismatch: '+name)
    return f

def approval(path):
    a=json.loads(pathlib.Path(path).read_text())
    if a != {'scope':SCOPE,'freeze_sha256':digest(FREEZE),'authorized':True,
             'cpu_seconds':150,'wall_seconds':240}:
        raise ValueError('explicit exact-scope budget approval required')
    return a

class Budget:
    def __init__(self,limits,cpuclock=None,wallclock=None):
        self.limits=limits
        self.cpuclock=cpuclock or self.cpu
        self.wallclock=wallclock or time.monotonic
        self.c0=self.cpuclock();self.t0=self.wallclock()
    @staticmethod
    def cpu():
        r=resource.getrusage(resource.RUSAGE_CHILDREN)
        return time.process_time()+r.ru_utime+r.ru_stime
    def cost(self):
        return {'accounted_cpu_seconds':self.cpuclock()-self.c0+self.limits['preparation_cpu_charge'],
                'accounted_wall_seconds':self.wallclock()-self.t0+self.limits['preparation_wall_charge'],
                'preparation_charge_is_not_measured':True}
    def can_dispatch(self):
        c=self.cost();l=self.limits
        return (c['accounted_cpu_seconds']+l['worker_cpu_seconds']+l['final_reserve_seconds']<=l['total_cpu_seconds'] and
                c['accounted_wall_seconds']+l['worker_wall_seconds']+l['cleanup_seconds']+l['final_reserve_seconds']<=l['total_wall_seconds'])
    def within(self):
        c=self.cost();return c['accounted_cpu_seconds']<=self.limits['total_cpu_seconds'] and c['accounted_wall_seconds']<=self.limits['total_wall_seconds']

def test_gate(commit_path,params,freeze_sha):
    c=json.loads(commit_path.read_text())
    if c['freeze_sha256']!=freeze_sha or c['params']!=list(params) or c['design_complete'] is not True:
        raise ValueError('test requires persisted matching winner commitment')
    return c

def collect(proc,timeout):
    timed_out=False
    try:out,err=proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out=True;os.killpg(proc.pid,signal.SIGKILL);out,err=proc.communicate(timeout=1)
    return out,err,timed_out

def worker(stage,candidate,index,approval_path):
    approval(approval_path);f=verify()
    if json.loads((OUT/'approval_claim.json').read_text())!=approval(approval_path):raise ValueError('approval not claimed')
    candidate=int(candidate);index=int(index)
    if stage not in ('design','test') or not 0<=candidate<27 or not 0<=index<5:raise ValueError('invalid slot')
    params=tuple(f['candidates'][candidate])
    if stage=='test':test_gate(OUT/'winner_commit.json',params,digest(FREEZE))
    l=f['limits'];resource.setrlimit(resource.RLIMIT_CPU,(l['worker_cpu_seconds'],)*2)
    resource.setrlimit(resource.RLIMIT_AS,(l['worker_address_space_bytes'],)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    import numpy as np
    from control import pack
    if np.__version__!=f['numpy_version']:raise ValueError('numpy version mismatch')
    values=json.loads((B/f['data']).read_text())['sets'][f['design_set'] if stage=='design' else f['test_set']][index]
    recorded=[]
    def warn(message,category,filename,lineno,file=None,line=None):
        if len(recorded)>=12000:raise RuntimeError('warning bound')
        recorded.append({'message':str(message),'category':category.__name__,'line':lineno})
    warnings.simplefilter('always');warnings.showwarning=warn
    with np.errstate(divide='warn',over='warn',invalid='warn',under='ignore'):r=pack(values,100,params)
    if recorded:raise ArithmeticError('unexpected warning at C100')
    r.update(stage=stage,candidate=candidate,index=index,warnings=recorded,numpy_version=np.__version__)
    print(json.dumps(r,separators=(',',':'),allow_nan=False))

def dispatch(stage,candidate,index,approval_path,budget,freeze):
    if not budget.can_dispatch():return {'status':'not_run_budget'}
    verify();name=f'{stage}_{candidate:02d}_{index}'
    if stage=='test':test_gate(OUT/'winner_commit.json',freeze['candidates'][candidate],digest(FREEZE))
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    before=Budget.cpu();start=time.monotonic()
    save(OUT/(name+'.started.json'),{'stage':stage,'candidate':candidate,'index':index,'cost':budget.cost()})
    p=subprocess.Popen([sys.executable,str(P/'run_once.py'),'worker',stage,str(candidate),str(index),str(approval_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True)
    out,err,timeout=collect(p,freeze['limits']['worker_wall_seconds'])
    (OUT/(name+'.stdout.json')).write_bytes(out);(OUT/(name+'.stderr.txt')).write_bytes(err)
    obs={'status':'complete' if p.returncode==0 and not err and not timeout else 'failed',
         'returncode':p.returncode,'timed_out':timeout,'reaped':p.poll() is not None,
         'cpu_seconds':Budget.cpu()-before,'wall_seconds':time.monotonic()-start,
         'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest()}
    if len(out)>2_000_000 or len(err)>16000:obs['status']='failed_output_bound'
    if obs['status']=='complete':obs['result']=json.loads(out)
    save(OUT/(name+'.json'),obs);return obs

def main(approval_path):
    # Validation precedes directory creation and every possible dispatch.
    approval_path=pathlib.Path(approval_path).resolve();a=approval(approval_path)
    f=json.loads(FREEZE.read_text());budget=Budget(f['limits']);f=verify()
    OUT.mkdir();save(OUT/'approval_claim.json',a)
    data=json.loads((B/f['data']).read_text())['sets']
    sys.path.insert(0,str(B));from paper_baseline_v1.src.checker import check_assignment
    from control import select_winner,fitness
    rows=[];stop=None;winner=None;results={};bounds=[]
    slots=[('design',j,i) for j in range(27) for i in range(5)]
    try:
        for stage,j,i in slots:
            obs=dispatch(stage,j,i,approval_path,budget,f)
            row={'stage':stage,'candidate':j,'index':i,'status':obs['status']}
            rows.append(row)
            if obs['status']!='complete':stop=obs['status'];break
            r=obs['result'];check=check_assignment(data[f['design_set']][i],100,r['assignment'],r['used_bins'],r['residuals'])
            row.update(used_bins=check['used_bins'],L1=check['L1'],ratio=check['L1']/check['used_bins'],cpu_seconds=obs['cpu_seconds'])
            results.setdefault(tuple(f['candidates'][j]),[]).append(check['used_bins'])
            if j==0:bounds.append(check['L1'])
            save(OUT/f'row_design_{j:02d}_{i}.json',row)
            if j==0 and i==4:
                old_report=json.loads((B/'paper_design_panel_v1/report.json').read_text())
                old_bins=[x['used_bins'] for x in old_report['rows'] if x['method']=='EOH']
                new_bins=results[tuple(f['candidates'][0])]
                save(OUT/'original_consistency.json',{'old_bins':old_bins,'new_bins':new_bins,
                     'equal':old_bins==new_bins,'meaning':'new worker consistency check, not independent scientific evidence'})
                if old_bins!=new_bins:raise ValueError('original configuration differs from verified design reference')
        if stop is None:
            verify();params=select_winner(bounds,results);winner=f['candidates'].index(list(params))
            exact=fitness(bounds,results[params])
            save(OUT/'winner_commit.json',{'design_complete':True,'freeze_sha256':digest(FREEZE),
                 'params':list(params),'candidate':winner,'fitness_fraction':str(exact),
                 'tie_rule':f['tie_rule'],'design_rows':rows.copy(),'cost':budget.cost()})
            test_gate(OUT/'winner_commit.json',params,digest(FREEZE))
            for i in range(5):
                obs=dispatch('test',winner,i,approval_path,budget,f)
                row={'stage':'test','candidate':winner,'index':i,'status':obs['status']};rows.append(row)
                if obs['status']!='complete':stop=obs['status'];break
                r=obs['result'];check=check_assignment(data[f['test_set']][i],100,r['assignment'],r['used_bins'],r['residuals'])
                row.update(used_bins=check['used_bins'],L1=check['L1'],ratio=check['L1']/check['used_bins'],cpu_seconds=obs['cpu_seconds'])
                save(OUT/f'row_test_{winner:02d}_{i}.json',row)
        verify()
    except Exception as e:stop=type(e).__name__+': '+str(e)
    # Preserve all unattempted planned slots without inventing a winner on failure.
    all_slots=slots+([('test',winner,i) for i in range(5)] if winner is not None else [])
    done={(r['stage'],r['candidate'],r['index']) for r in rows}
    for stage,j,i in all_slots:
        if (stage,j,i) not in done:rows.append({'stage':stage,'candidate':j,'index':i,'status':'not_run_after_stop'})
    if not budget.within():stop='observed_budget_exceeded'
    report={'status':'complete' if stop is None else 'stopped','stop_reason':stop,'rows':rows,
            'winner':winner,'cost':budget.cost(),'freeze_sha256':digest(FREEZE),
            'test_label':'exploratory reuse of public historical test data; not fresh heldout',
            'test_unselected_count':5 if winner is None else 0,
            'final_snapshot_note':'last bounded report write outside final measurement; 5-second reserve'}
    if stop is None:
        rr=[r for r in rows if r['stage']=='test'];report['test_fitness_fraction']=str(fitness([r['L1'] for r in rr],[r['used_bins'] for r in rr]))
    save(OUT/'report.json',report)
    print(json.dumps({k:report[k] for k in ['status','stop_reason','winner','cost']},ensure_ascii=False))

if __name__=='__main__':
    if len(sys.argv)==6 and sys.argv[1]=='worker':worker(*sys.argv[2:])
    elif len(sys.argv)==3 and sys.argv[1]=='--approval':main(sys.argv[2])
    else:raise SystemExit('Requires --approval PATH; no automatic execution')
