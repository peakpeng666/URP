"""Independent scalar score / integer replay checker. Does not import runner or selector."""
import pathlib,json,hashlib,math,heapq,time,resource,statistics
import numpy as np
H=pathlib.Path(__file__).resolve().parents[1]
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
sha=lambda x:hashlib.sha256(x).hexdigest()
def put(p,x):
    with p.open('x') as f:f.write(canon(x)+'\n')

def scalar_score(item,r):
    d=r-item;e=math.exp(d)
    return r/((e+.7)*e)+((1-d/r)*math.sqrt(d)+(.8 if d>item*3 else .3))

def rankings():
    out={}
    for item in range(1,101):
        groups={}
        for r in range(item,101):groups.setdefault(scalar_score(item,r),[]).append(r)
        out[item]=[(sum(1<<r for r in rs),rs) for score,rs in sorted(groups.items(),reverse=True)]
    return out

def independent_features(prefix,rem):
    u=[x for x in rem if x<100];s=sorted(prefix)
    def quantile(q):
        z=499*q;a=int(z);b=min(a+1,499);return (s[a]+(s[b]-s[a])*(z-a))/100
    return [sum((x-1)//10==b for x in prefix)/500 for b in range(10)]+[statistics.mean(prefix)/100,statistics.pstdev(prefix)/100]+[quantile(q) for q in [.1,.5,.9]]+[sum(b>a for a,b in zip(prefix,prefix[1:]))/499,sum(b<a for a,b in zip(prefix,prefix[1:]))/499,(statistics.mean(prefix[-100:])-statistics.mean(prefix[:100]))/100,len(u)/500]+[sum(x//10==b for x in u)/len(u) for b in range(10)]+[statistics.mean(u)/100,statistics.pstdev(u)/100]

def replay(data,row,ranks):
    archive=H/row['trajectory_file'];assert sha(archive.read_bytes())==row['trajectory_sha256']
    with np.load(archive) as loaded:z={k:loaded[k] for k in loaded.files}
    rem=[100]*5000;counts=[0]*101;counts[100]=5000;heaps=[[] for _ in range(101)];heaps[100]=list(range(5000));present=1<<100;used=0;prefix=None
    assert row['status']=='complete' and row['steps']==5000 and len(z['assignment'])==5000
    assert row['items_sha256']==sha(canon(data['items']).encode())
    for step,(item,target) in enumerate(zip(data['items'],z['assignment'].tolist())):
        is_eoh=row['policy']=='published_EoH' or (step>=500 and row['branch']=='BF_then_EoH')
        if is_eoh:
            possible=None
            for mask,rs in ranks[item]:
                if mask&present:possible=[r for r in rs if counts[r]];break
            assert possible is not None
        else:
            m=present>>item;assert m;possible=[item+(m&-m).bit_length()-1]
        candidates=[]
        for r in possible:
            while heaps[r] and rem[heaps[r][0]]!=r:heapq.heappop(heaps[r])
            assert heaps[r];candidates.append(heaps[r][0])
        expected=min(candidates);assert target==expected,(data['instance_id'],row['policy'],step,target,expected)
        before=rem[target];after=before-item
        assert 0<=after<100 and before>=item
        assert int(z['pre_remaining'][step])==before and int(z['post_remaining'][step])==after
        assert int(z['feasible_counts'][step])==sum(counts[item:])
        used+=int(before==100);assert int(z['used_bins_after'][step])==used
        rem[target]=after;counts[before]-=1;counts[after]+=1
        if counts[before]==0:present&=~(1<<before)
        present|=1<<after;heapq.heappush(heaps[after],target)
        if step==499:prefix=rem.copy()
    assert rem==z['remaining'].tolist() and used==row['used_bins'] and used==sum(r<100 for r in rem)
    assert sum(100-r for r in rem)==sum(data['items']) and used>=(sum(data['items'])+99)//100
    assert row['prefix_remaining_sha256']==sha(canon(prefix).encode())
    f=independent_features(data['items'][:500],prefix)
    assert np.allclose(f,row['prefix_features'],rtol=1e-13,atol=1e-14)
    return prefix,z['assignment'].tolist(),f

def main():
    resource.setrlimit(resource.RLIMIT_CPU,(240,240));cpu=time.process_time();wall=time.monotonic();ranks=rankings()
    protocol=json.loads((H/'PROTOCOL.json').read_bytes());model=json.loads((H/'MODEL.json').read_bytes());mf=json.loads((H/'MODEL_FREEZE.json').read_bytes())
    assert sha((H/'MODEL.json').read_bytes())==mf['model_sha256'];train=[];risk={};runs=0;selection_checks=0;traces={}
    for meta in protocol['instances']:
        data=json.loads((H/'inputs'/f"{meta['instance_id']}.json").read_bytes())
        assert len(data['items'])==5000 and all(type(x)==int and 1<=x<=100 for x in data['items'])
        assert sha(canon(sorted(data['items'])).encode())==meta['multiset_sha256']
        methods=['BF','BF_then_EoH'] if meta['split']=='train' else ['BF','BF_then_EoH','published_EoH','SELECTOR']
        rows={};assignments={};states={};features={}
        for p in methods:
            row=json.loads((H/'raw'/f"{meta['instance_id']}__{p}.json").read_bytes());rows[p]=row
            states[p],assignments[p],features[p]=replay(data,row,ranks);runs+=1
        assert states['BF']==states['BF_then_EoH'] and assignments['BF'][:500]==assignments['BF_then_EoH'][:500]
        if meta['split']=='train':train.append((meta['instance_id'],features['BF'],[rows[p]['used_bins'] for p in methods]))
        else:
            sel=rows['SELECTOR'];branch=sel['branch']
            assert assignments['SELECTOR']==assignments[branch] and states['SELECTOR']==states['BF'] and sel['selector_consumed_count']==500
            f=sel['prefix_features'];z=(np.array(f)-np.array(model['mean']))/np.array(model['scale'])
            distances=np.sum((np.array(model['x'])-z)**2,axis=1).tolist()
            nn=sorted(range(144),key=lambda i:(distances[i],i))[:5];costs=[sum(model['y'][i][j] for i in nn)/5 for j in range(2)]
            ix=model['sbs_index'] if costs[0]==costs[1] else int(costs[1]<costs[0])
            assert nn==sel['decision']['neighbors'] and costs==sel['decision']['predicted_final_bins']
            assert ix==sel['decision']['selected_index'];selection_checks+=1
            if meta['split']=='risk':risk.setdefault(meta['group_id'],[]).append({'prefix':data['items'][:500],'state':states['BF'],'features':sel['prefix_features'],'decision':sel['decision'],'branch':branch})
        print(canon({'checked_runs':runs,'id':meta['instance_id']}),flush=True)
    assert [r[0] for r in train]==mf['training_rows'];X=np.array([r[1] for r in train]);Y=np.array([r[2] for r in train]);mu=X.mean(0);sd=X.std(0);sd[sd==0]=1
    assert np.allclose(mu,model['mean'],atol=1e-14,rtol=1e-13) and np.allclose(sd,model['scale'],atol=1e-14,rtol=1e-13)
    assert np.allclose((X-mu)/sd,model['x'],atol=1e-12,rtol=1e-12) and Y.tolist()==model['y']
    assert int(np.argmin(Y.mean(0)))==model['sbs_index']
    for group,rr in risk.items():assert len(rr)==3 and rr[0]==rr[1]==rr[2],group
    group_sets={s:{r['multiset_sha256'] for r in protocol['instances'] if r['split']==s} for s in ['train','confirmation','risk']}
    assert not group_sets['train']&group_sets['confirmation'] and not group_sets['train']&group_sets['risk']
    for n,h in json.loads((H/'FREEZE.json').read_bytes())['files'].items():assert sha((H/n).read_bytes())==h,n
    result={'passed':True,'full_runs_checked':runs,'integer_and_decision_steps':runs*5000,'selector_decisions_checked':selection_checks,'same_prefix_future_invariance_groups':len(risk),'training_fit_recomputed':True,'full_selected_trace_matches_chosen_continuation':True,'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-wall,'scope':'Independent math scalar EoH ranking; exact integer full-state replay; independently coded features and neighbor prediction. Not adversarial isolation or universal online guarantee.'}
    put(H/'CHECK.json',result);print(canon(result))
if __name__=='__main__':main()
