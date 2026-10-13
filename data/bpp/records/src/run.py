"""Complete real executions of allowlisted policies and the prefix-only selector."""
import pathlib,hashlib,json,time,resource,traceback,os,signal
import numpy as np
from selector import fit,features,choose,BRANCHES
H=pathlib.Path(__file__).resolve().parents[1]
ALLOW={'BF':'f1b3010016ca5c3c95a5f583ddc071cd1a30cfaf40e270b865c95f4817387d4b','published_EoH':'de06105a3b630fc5ab6f2d823e45d5326315071208cbac8379ffe8d3a29bed7a'}
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
sha=lambda x:hashlib.sha256(x).hexdigest()
def put(p,x):
    with p.open('x') as f:f.write(canon(x)+'\n');f.flush()
def verify():
    for n,h in json.loads((H/'FREEZE.json').read_bytes())['files'].items():assert sha((H/n).read_bytes())==h,n

def load_controls():
    out={}
    for p,h in ALLOW.items():
        b=(H/'sources'/f'{p}.py.txt').read_bytes(); assert sha(b)==h
        scope={'np':np,'__builtins__':{}};exec(compile(b,f'<trusted-control-{p}>','exec'),scope);out[p]=scope['score']
    return out

class ArrivalStream:
    def __init__(self,items):self._iterator=iter(items);self.consumed=0
    def __iter__(self):return self
    def __next__(self):
        item=next(self._iterator);self.consumed+=1;return item

def execute(data,policy,controls,model=None):
    start=time.monotonic();cpu=time.process_time();n=5000
    rem=np.full(n,100,dtype=np.int64);used=0;arrived=[];stream=ArrivalStream(data['items'])
    fields=('assignment','pre_remaining','post_remaining','feasible_counts','used_bins_after')
    tr={k:np.empty(n,dtype=np.int32) for k in fields};steps=0;status='complete';error=None
    choice='BF' if policy=='BF' else ('BF_then_EoH' if policy=='BF_then_EoH' else 'published_EoH')
    decision=None;instrument_feature_cpu=0.;selection_cpu=0.;prefix_hash=None;prefix_features=None;reads=None
    try:
        with np.errstate(all='raise'):
            for item in stream:
                algorithm='published_EoH' if policy=='published_EoH' else ('BF' if steps<500 or choice=='BF' else 'published_EoH')
                feasible=np.flatnonzero(rem>=item);bins=np.array(rem[feasible],dtype=np.int64,copy=True);bins.setflags(write=False)
                scores=controls[algorithm](np.int64(item),bins)
                assert isinstance(scores,np.ndarray) and scores.shape==bins.shape and np.all(np.isfinite(scores))
                target=int(feasible[int(np.argmax(scores))]);before=int(rem[target]);rem[target]-=item
                used+=int(before==100); assert rem[target]>=0
                for key,value in zip(fields,(target,before,int(rem[target]),len(feasible),used)):tr[key][steps]=value
                steps+=1
                if steps<=500:arrived.append(item)
                if steps==500:
                    prefix_hash=sha(canon(rem.tolist()).encode());reads=stream.consumed
                    if policy=='SELECTOR':
                        t=time.process_time();choice,decision=choose(tuple(arrived),tuple(map(int,rem)),model);selection_cpu=time.process_time()-t
                        prefix_features=decision['features']; assert reads==500
                    else:
                        t=time.process_time();prefix_features=features(tuple(arrived),tuple(map(int,rem))).tolist();instrument_feature_cpu=time.process_time()-t
            assert steps==n
    except BaseException as e:
        status='failure';error=type(e).__name__+': '+str(e)
    loop_cpu=time.process_time()-cpu;loop_wall=time.monotonic()-start
    stem=f"{data['instance_id']}__{policy}"
    rawpath=H/'raw'/f'{stem}.npz'
    with rawpath.open('xb') as f:np.savez_compressed(f,**{k:v[:steps] for k,v in tr.items()},remaining=rem)
    row={'instance_id':data['instance_id'],'policy':policy,'status':status,'error':error,'steps':steps,'used_bins':used,'items_sha256':sha(canon(data['items']).encode()),'trajectory_file':str(rawpath.relative_to(H)),'trajectory_sha256':sha(rawpath.read_bytes()),'prefix_remaining_sha256':prefix_hash,'prefix_features':prefix_features,'selector_consumed_count':reads,'branch':choice,'decision':decision,'cpu_loop_seconds':loop_cpu,'cpu_policy_seconds':loop_cpu-selection_cpu-instrument_feature_cpu,'cpu_selector_seconds':selection_cpu,'cpu_instrument_feature_seconds':instrument_feature_cpu,'wall_loop_seconds':loop_wall,'cpu_total_including_serialization_seconds':time.process_time()-cpu}
    put(H/'raw'/f'{stem}.json',row)
    if error:raise RuntimeError(error)
    return row

def cpu_limit_handler(signum,frame):
    raise RuntimeError('Numerical soft CPU limit580 reached; saving partial failure before hard600')

def main():
    signal.signal(signal.SIGXCPU,cpu_limit_handler)
    resource.setrlimit(resource.RLIMIT_CPU,(580,600));verify();controls=load_controls()
    protocol=json.loads((H/'PROTOCOL.json').read_bytes());start=time.monotonic();cpu=time.process_time()
    put(H/'RUN_STARTED.json',{'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'freeze_sha256':sha((H/'FREEZE.json').read_bytes()),'numerical_cpu_limit':600,'numerical_soft_cpu_limit':580,'single_thread_env':{k:os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']}})
    rows=[];x=[];y=[];ids=[]
    try:
        for meta in protocol['instances']:
            if meta['split']!='train':continue
            data=json.loads((H/'inputs'/f"{meta['instance_id']}.json").read_bytes())
            r=[execute(data,p,controls) for p in BRANCHES];rows.extend(r)
            assert r[0]['prefix_remaining_sha256']==r[1]['prefix_remaining_sha256'] and r[0]['prefix_features']==r[1]['prefix_features']
            x.append(r[0]['prefix_features']);y.append([a['used_bins'] for a in r]);ids.append(meta['instance_id'])
            print(canon({'stage':'train','completed_runs':len(rows),'instance':meta['instance_id'],'bins':y[-1]}),flush=True)
        t=time.process_time();model=fit(x,y);fit_cpu=time.process_time()-t
        put(H/'MODEL.json',model)
        put(H/'MODEL_FREEZE.json',{'model_sha256':sha((H/'MODEL.json').read_bytes()),'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'fit_cpu_seconds':fit_cpu,'training_rows':ids,'training_labels':y,'training_mean_bins':np.mean(y,axis=0).tolist(),'training_oracle_mean_bins':float(np.min(y,axis=1).mean()),'training_sbs':BRANCHES[model['sbs_index']],'before_confirmation_execution':True})
        print(canon({'stage':'fit','sbs':BRANCHES[model['sbs_index']],'mean_costs':np.mean(y,axis=0).tolist(),'model_hash':sha((H/'MODEL.json').read_bytes())}),flush=True)
        for meta in protocol['instances']:
            if meta['split']=='train':continue
            data=json.loads((H/'inputs'/f"{meta['instance_id']}.json").read_bytes())
            # Fixed order is rotated by stream to reduce timing-position confounding.
            names=['BF','BF_then_EoH','published_EoH','SELECTOR'];offset=(len(rows)//4)%4;names=names[offset:]+names[:offset]
            r=[execute(data,p,controls,model) for p in names];rows.extend(r)
            assert sha((H/'MODEL.json').read_bytes())==json.loads((H/'MODEL_FREEZE.json').read_bytes())['model_sha256']
            print(canon({'stage':meta['split'],'completed_runs':len(rows),'instance':meta['instance_id'],'bins':{v['policy']:v['used_bins'] for v in r},'choice':next(v['branch'] for v in r if v['policy']=='SELECTOR')}),flush=True)
        assert len(rows)==768;verify()
        put(H/'RUN_COMPLETE.json',{'status':'complete','full_runs':len(rows),'total_cpu_seconds':time.process_time()-cpu,'total_wall_seconds':time.monotonic()-start,'model_fit_cpu_seconds':fit_cpu,'model_calls':0,'api_charges':0,'finished_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    except BaseException as e:
        put(H/'RUN_FAILURE.json',{'error':type(e).__name__+': '+str(e),'completed_runs':len(rows),'cpu_seconds':time.process_time()-cpu,'traceback':traceback.format_exc()});raise
if __name__=='__main__':main()
