"""Single fixed design panel, exact reviewed author-source gate, no model calls."""
import os,sys,json,pathlib,hashlib,time,resource,subprocess,signal,warnings
P=pathlib.Path(__file__).resolve().parent; B=P.parent
AUTHOR=B/'published_eoh_readiness/upstream/examples/bp_online/evaluation/heuristic_original_EoH_paper.py'
TRUSTED=B/'published_eoh_formula_v1/src/formula.py'
DATA=B/'paper_baseline_v1/data/historical_numeric.json'
SHA='f3d50f0e81ca061a0377b9fb61b75cf16ecde9f091876db0d8baca8323655995'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
 path=P/name
 with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
def fixed_functions():
 assert digest(AUTHOR)==SHA
 original={};exec(compile(AUTHOR.read_bytes(),str(AUTHOR),'exec'),original)
 # Only exact reviewed fixed formula, adapting scalar guard to the original design dtype.
 source=TRUSTED.read_text();assert source.count('type(item) is not np.int32')==1
 adapted=source.replace('type(item) is not np.int32','type(item) is not np.int64')
 native={};exec(compile(adapted,str(TRUSTED)+'#int64_guard_only','exec'),native)
 return original['score'],native['score']
def worker(mode,index=None,method=None):
 resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_AS,(2**31,2**31))
 resource.setrlimit(resource.RLIMIT_FSIZE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
 import numpy as np
 assert np.__version__=='2.3.5'
 recorded=[]
 def warn(message,category,filename,lineno,file=None,line=None):
  if len(recorded)>=12000:raise RuntimeError('warning bound')
  recorded.append({'message':str(message),'category':category.__name__,'filename':filename,'line':lineno})
 warnings.simplefilter('always');warnings.showwarning=warn
 with np.errstate(divide='warn',over='warn',invalid='warn',under='ignore'):
  if mode=='gate':
   original,trusted=fixed_functions();cases=0;pairs=0;hs=hashlib.sha256()
   for i in range(1,101):
    item=np.int64(i);base=np.arange(i,501,dtype=np.int64)
    layouts=[base,base[::-1],np.repeat(base[:1],17),np.resize(base,5000),np.array([i,i,500,500],dtype=np.int64)]
    for bins in layouts:
     before=bins.tobytes();a=original(item,bins);b=trusted(item,bins)
     assert bins.tobytes()==before and a.dtype==b.dtype==np.dtype('float64')
     assert a.tobytes()==b.tobytes() and int(np.argmax(a))==int(np.argmax(b)) and np.all(np.isfinite(a))
     hs.update(a.tobytes());cases+=1;pairs+=len(bins)
   assert all(x['category']=='RuntimeWarning' and x['message']=='overflow encountered in multiply' for x in recorded)
   result={'pass':True,'vector_cases':cases,'scalar_pairs':pairs,'bitwise_equal':True,'first_argmax_equal':True,'scores_sha256':hs.hexdigest(),'item_dtype':'int64','bins_dtype':'int64','author_source_sha256':SHA}
  else:
   items=json.loads(DATA.read_text())['sets']['historical_design_5k'][int(index)];assert len(items)==5000
   if method in ['FF','BF']:
    sys.path.insert(0,str(B));from paper_baseline_v1.src.baselines import pack
    result=pack(items,100,method)
   else:
    # Formal slots use trusted formula only, not downloaded source.
    source=TRUSTED.read_text().replace('type(item) is not np.int32','type(item) is not np.int64')
    ns={};exec(compile(source,str(TRUSTED)+'#int64_guard_only','exec'),ns);score=ns['score']
    residuals=np.full(5000,100,dtype=np.int64);assign=[];counts=[]
    for item in np.asarray(items,dtype=np.int64):
     ids=np.flatnonzero(residuals-item>=0);scores=score(item,residuals[ids]);chosen=int(ids[int(np.argmax(scores))]);residuals[chosen]-=item;assign.append(chosen);counts.append(int(ids.size))
    result={'assignment':assign,'residuals':residuals.tolist(),'used_bins':int(np.count_nonzero(residuals!=100)),'feasible_counts':counts,'n_bin_feasibility_checks':5000**2}
   assert not recorded
   result.update({'instance_index':int(index),'method':method,'item_dtype':'int64','capacity':100})
 result.update({'warnings':recorded,'numpy_version':np.__version__,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
 print(json.dumps(result,separators=(',',':'),allow_nan=False))
def main():
 start=time.monotonic();cpu0=time.process_time();child0=resource.getrusage(resource.RUSAGE_CHILDREN)
 def cost():
  ch=resource.getrusage(resource.RUSAGE_CHILDREN)
  return {'measured_cpu_seconds':time.process_time()-cpu0+ch.ru_utime+ch.ru_stime-child0.ru_utime-child0.ru_stime,'wall_seconds':time.monotonic()-start,'static_preparation_budget_charge_cpu_seconds':3,'static_preparation_budget_charge_wall_seconds':3}
 def call(args,name):
  c=cost()
  if c['measured_cpu_seconds']+3+5+2>60 or c['wall_seconds']+3+10+2>120:return {'status':'not_run_budget'}
  env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
  before=resource.getrusage(resource.RUSAGE_CHILDREN);t=time.monotonic();p=subprocess.Popen([sys.executable,str(P/'run_once.py'),'worker',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True)
  timeout=False
  try:out,err=p.communicate(timeout=10)
  except subprocess.TimeoutExpired:
   timeout=True;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate(timeout=1)
  after=resource.getrusage(resource.RUSAGE_CHILDREN)
  (P/(name+'.stdout.json')).write_bytes(out);(P/(name+'.stderr.txt')).write_bytes(err)
  obs={'status':'complete' if p.returncode==0 and not err and not timeout else 'failed','returncode':p.returncode,'timeout':timeout,'cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'wall_seconds':time.monotonic()-t,'stdout_bytes':len(out),'stderr_bytes':len(err),'reaped':p.poll() is not None}
  if len(out)>2_000_000 or len(err)>16000:obs['status']='failed_output_bound'
  if obs['status']=='complete':obs['result']=json.loads(out)
  save(name+'.json',obs);return obs
 save('source_verification.json',{'author_sha256':digest(AUTHOR),'expected_sha256':SHA,'author_bytes':AUTHOR.stat().st_size,'provenance':json.loads((B/'published_eoh_readiness/source_provenance.json').read_text()),'historical_data_sha256':digest(DATA),'note':'Author formula is pinned 2026 repo labeled original paper, not proved to have existed in 2024. Historical design data is pinned 2024.'})
 assert digest(AUTHOR)==SHA
 gate=call(['gate'],'numeric_gate')
 if gate['status']!='complete':save('stopped.json',{'reason':'gate failure','cost':cost()});return
 design=json.loads(DATA.read_text())['sets']['historical_design_5k']
 protocol={'schema':1,'source_hashes':{str(x.relative_to(B)):digest(x) for x in [AUTHOR,TRUSTED,DATA,P/'run_once.py',B/'paper_baseline_v1/src/baselines.py',B/'paper_baseline_v1/src/checker.py']},'methods':['FF','BF','EOH'],'capacity':100,'instances':[{'index':i,'n':len(x),'sum':sum(x),'L1':(sum(x)+99)//100,'sha256':hashlib.sha256(json.dumps(x,separators=(',',':')).encode()).hexdigest()} for i,x in enumerate(design)],'dtype':'int64 items and residuals; trusted formula only changes scalar guard np.int32 to np.int64','metrics':['mean(L1_i/used_bins_i)','(sum(used_bins_i)-sum(L1_i))/sum(L1_i)'],'selection':'all feasible preallocated bins, including unused; stable first argmax','gate_sha256':digest(P/'numeric_gate.json'),'limits':{'total_cpu_seconds':60,'total_wall_seconds':120,'worker_cpu_seconds':5,'worker_wall_seconds':10,'worker_address_space_bytes':2**31,'serial':True,'retries':0},'cost_before_freeze':cost(),'slots':[{'index':i,'method':m} for i in range(5) for m in ['FF','BF','EOH']]}
 save('protocol_frozen.json',protocol)
 sys.path.insert(0,str(B));from paper_baseline_v1.src.checker import check_assignment
 rows=[];failed=False
 for i,m in [(i,m) for i in range(5) for m in ['FF','BF','EOH']]:
  name=f'slot_{i}_{m}'
  obs={'status':'not_run_after_failure'} if failed else call(['pack',str(i),m],name)
  row={'instance_index':i,'method':m,'status':obs['status'],'observation':name+'.json'}
  if obs['status']=='complete':
   r=obs['result'];checked=check_assignment(design[i],100,r['assignment'],r['used_bins'],r['residuals']);row.update({k:checked[k] for k in ['used_bins','L1','excess_bins','per_instance_excess']});row['fitness']=checked['L1']/checked['used_bins'];row['worker_cpu_seconds']=obs['cpu_seconds']
  else:failed=True
  rows.append(row);save(f'row_{i}_{m}.json',row)
 groups=[]
 for m in ['FF','BF','EOH']:
  rr=[r for r in rows if r['method']==m and r['status']=='complete']
  if len(rr)==5:
   bins=sum(r['used_bins'] for r in rr);lb=sum(r['L1'] for r in rr)
   groups.append({'method':m,'sum_bins':bins,'sum_L1':lb,'mean_bins':bins/5,'paper_mean_L1_over_bins':sum(r['fitness'] for r in rr)/5,'aggregate_excess':(bins-lb)/lb,'mean_instance_excess':sum(r['per_instance_excess'] for r in rr)/5})
 save('report.json',{'rows':rows,'groups':groups,'cost':cost(),'protocol_sha256':digest(P/'protocol_frozen.json'),'gate_passed':True,'no_retries':True,'verification':'Independent saved assignment load/capacity/bin/L1 check; no second floating-score trajectory replay','cost_note':'3s static preparation budget charge is not measured preparation cost. Final JSON/output after last snapshot unmetered; 2s reserved.'})
 print(json.dumps({'groups':groups,'cost':cost(),'completed':sum(r['status']=='complete' for r in rows)},ensure_ascii=False))
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':worker(*sys.argv[2:])
 else:main()
