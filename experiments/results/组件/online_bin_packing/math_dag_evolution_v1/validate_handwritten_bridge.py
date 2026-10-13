"""Three fixed handwritten micro-packings; no study cases, model or tokenizer."""
import copy,hashlib,json,pathlib,resource,sys,time
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from scoring import run_score,check_observation
from guard import sha

def snapshot_check():
 d=json.loads((ROOT/'prevalidation_snapshot.json').read_bytes())
 for rel,want in d['files'].items():
  if sha(ROOT/rel)!=want:raise ValueError('prevalidation source changed: '+rel)
 return sha(ROOT/'prevalidation_snapshot.json')
def main():
 start=time.monotonic();cpu=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
 resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(30,30))
 digest=snapshot_check();out=ROOT/'logs/handwritten_bridge_01';out.mkdir(parents=True,exist_ok=False);rows=[];negative=[]
 cases=[('ff',ROOT/'seeds/ff.json',[6,4,5,5],10),('bf',ROOT/'seeds/bf.json',[6,4,5,5],10),('formula',ROOT.parent/'math_dag_v1/fixtures/programs/published_eoh.json',[1,4,2,3,7,1],10)]
 for name,path,items,capacity in cases:
  raw=path.read_bytes();case={'id':'handwritten_'+name,'items':items,'capacity':capacity};checked,obs=run_score(raw,case,out/name)
  if checked['status']!='completed_valid':raise ValueError('handwritten packing failed')
  if name in {'ff','bf'} and checked['assignment']!=[0,0,1,1]:raise ValueError('handwritten FF/BF expected assignment')
  rows.append({'id':name,'checked':checked,'pid':obs['pid'],'worker_cpu_seconds':obs['worker_cpu_seconds'],'worker_peak_rss_kib':obs['worker_peak_rss_kib'],'wall_seconds':obs['wall_seconds'],'reaped':obs['reaped']})
  if name=='ff':
   for label,mutate in [('wrong_source',lambda x:x['result'].update(program_sha256='0'*64)),('bad_assignment',lambda x:x['result']['result']['assignment'].__setitem__(0,999)),('unclean_exit',lambda x:x.update(returncode=1)),('bad_warning_event',lambda x:x['result']['warnings'].update(events=[[0,0,0]]))]:
    fake=copy.deepcopy(obs);mutate(fake)
    try:check_observation(raw,case,fake)
    except Exception as exc:negative.append({'id':label,'rejected':True,'type':type(exc).__name__})
    else:raise ValueError('malformed observation accepted: '+label)
 if snapshot_check()!=digest:raise ValueError('snapshot manifest changed')
 after=resource.getrusage(resource.RUSAGE_CHILDREN);child=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime
 result={'status':'passed','snapshot_sha256':digest,'requests':3,'distinct_pids':len({r['pid'] for r in rows}),'rows':rows,'malformed_observations':negative,'model_calls':0,'formal_study_score_calls':0,'supervisor_cpu_seconds':time.process_time()-cpu,'children_cpu_seconds':child,'recorded_worker_cpu_seconds':sum(r['worker_cpu_seconds'] for r in rows),'wall_seconds':time.monotonic()-start,'scope':'Fixed tiny handwritten controls only; no prospective128-item design/validation sequence was scored.'}
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
