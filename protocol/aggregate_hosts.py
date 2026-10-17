"""Derived, host-stratified summary; never changes frozen protocol or raw results."""
import argparse,csv,hashlib,itertools,json
from collections import defaultdict
from pathlib import Path
from aggregate import aggregate as base_aggregate, summarize, equal_mean,mean

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def context(path,runroot,expected_plan_sha256=None):
    """Resolve the nearest manifest, without treating declarations as evidence.

    A nearer incomplete manifest blocks inheritance from an older parent scope.
    Verification here binds the recorded host/resource context to the archived
    environment bytes; it is not independent measurement of the hardware.
    """
    if not path:return {}
    p=Path(path).resolve();roots=runroot if isinstance(runroot,(list,tuple)) else [runroot]
    containing=[Path(r).resolve() for r in roots if Path(r).resolve() in p.parents]
    if not containing:return {}
    root=max(containing,key=lambda x:len(x.parts))
    for parent in p.parents:
        if parent!=root and root not in parent.parents:break
        f=parent/'host_manifest.json'
        if f.exists():
            evidence={'host_evidence':str(f)}
            try:
                evidence['host_manifest_sha256']=sha(f)
                m=json.loads(f.read_text())
                if not isinstance(m,dict):raise ValueError('manifest must be an object')
                if m.get('verification_status')!='VERIFIED':
                    return dict(evidence,metadata_error='HOST_MANIFEST_NOT_VERIFIED')
                if any(not isinstance(m.get(k),str) or not m[k].strip() or m[k]=='unknown' for k in ('host_id','resource_cohort')):
                    return dict(evidence,metadata_error='HOST_MANIFEST_INVALID_IDENTITY')
                if expected_plan_sha256 is not None and m.get('canonical_plan_sha256')!=expected_plan_sha256:
                    return dict(evidence,metadata_error='HOST_PLAN_HASH_MISMATCH')
                ep=m.get('environment_manifest_path')
                if not isinstance(ep,str) or not ep or Path(ep).is_absolute():
                    return dict(evidence,metadata_error='HOST_ENVIRONMENT_PATH_INVALID')
                hp=(parent/ep).resolve()
                if root not in hp.parents or not hp.is_file() or sha(hp)!=m.get('environment_manifest_sha256'):
                    return dict(evidence,metadata_error='HOST_ENVIRONMENT_HASH_MISMATCH')
                return dict(evidence,host_id=m['host_id'],resource_cohort=m['resource_cohort'],host_verified=True)
            except (OSError,ValueError,TypeError):
                return dict(evidence,metadata_error='HOST_MANIFEST_INVALID')
    return {}
def scoped_summary(rows):
    out=summarize(rows);hosts={(r['host_id'],r['resource_cohort']) for r in rows if r['started']}
    verified=sum(r['started'] and r['host_verified'] for r in rows)
    if len(hosts)!=1 or any('unknown' in h for h in hosts) or verified!=out['started']:out['cpu_seconds_mean_started']=None
    out['timing_scope']='single verified host/resource cohort' if out['cpu_seconds_mean_started'] is not None else 'not pooled across hosts/cohorts or missing provenance'
    out['host_resource_cohorts']=[list(h) for h in sorted(hosts)]
    out['verified_host_rows']=verified
    out['unverified_host_rows_started']=out['started']-verified
    return out

def aggregate_hosts(plan,cases,dist,root,assignment):
    rows,old=base_aggregate(plan,cases,dist,root,assignment.get('canonical_plan_sha256'))
    owners={}
    for host,config in assignment.get('machines',{}).items():
        if not isinstance(host,str) or not host.strip():raise ValueError('Invalid assigned host')
        for seed in config['seeds']:
            if type(seed) is not int or seed<0 or seed in owners:raise ValueError('Duplicate or invalid seed ownership')
            owners[seed]=host
    for row in rows:
        row.update(assigned_host_id=owners.get(row['seed'],'unknown'),host_id='unknown',resource_cohort='unknown',host_verified=False,declared_host_id=None,declared_resource_cohort=None,host_evidence=None,host_manifest_sha256=None,host_provenance_error=None)
        if row['started']:
            r=json.loads(Path(row['result_path']).read_text());ctx=context(row['result_path'],root,assignment.get('canonical_plan_sha256'));declared=r.get('host_id',r.get('machine_id'))
            row.update(declared_host_id=declared,declared_resource_cohort=r.get('resource_cohort',r.get('resource_batch_id')))
            row.update({k:v for k,v in ctx.items() if k in ('host_evidence','host_manifest_sha256')})
            if ctx.get('metadata_error'):row['host_provenance_error']=ctx['metadata_error']
            elif r.get('host_id') and r.get('machine_id') and r['host_id']!=r['machine_id']:row['host_provenance_error']='HOST_DECLARATION_CONFLICT'
            elif declared and ctx.get('host_id') and declared!=ctx['host_id']:row['host_provenance_error']='HOST_DECLARATION_CONFLICT'
            elif row['declared_resource_cohort'] and ctx.get('resource_cohort') and row['declared_resource_cohort']!=ctx['resource_cohort']:row['host_provenance_error']='RESOURCE_COHORT_DECLARATION_CONFLICT'
            elif ctx.get('host_verified'):
                row.update(ctx)
            if not row['host_verified']:row['host_provenance_error']=row['host_provenance_error'] or 'HOST_EXECUTION_PROVENANCE_MISSING'
        else:
            row['host_id']=row['assigned_host_id'];row['resource_cohort']='not_started';row['host_evidence']='planned allocation only'
    for row in rows:
        row['assignment_mismatch']=bool(row['started'] and row['host_id'] not in ('unknown',row['assigned_host_id']) and row['assigned_host_id']!='unknown')
    groups={}
    for axis in ('overall','size_stratum','distribution','source_family','contract_id'):
        pooled=defaultdict(list);byhost=defaultdict(list)
        for r in rows:
            group='all' if axis=='overall' else r[axis]
            pooled[(r['algorithm'],group)].append(r)
            byhost[(r['host_id'],r['resource_cohort'],r['algorithm'],group)].append(r)
        groups[axis]={'pooled_quality_descriptive':[dict(algorithm=a,group=g,**scoped_summary(v)) for (a,g),v in sorted(pooled.items())], 'by_host_resource':[dict(host_id=h,resource_cohort=c,algorithm=a,group=g,**scoped_summary(v)) for (h,c,a,g),v in sorted(byhost.items())]}
    ownership=[]
    for h in sorted(set(r['assigned_host_id'] for r in rows)):
        for a in plan['algorithms']:
            rr=[r for r in rows if r['assigned_host_id']==h and r['algorithm']==a]
            ownership.append(dict(assigned_host_id=h,algorithm=a,**scoped_summary(rr)))
    pairs=[]
    for a,b in itertools.combinations(plan['algorithms'],2):
        ar={(r['case_id'],r['seed']):r for r in rows if r['algorithm']==a};br={(r['case_id'],r['seed']):r for r in rows if r['algorithm']==b};buckets=defaultdict(list);rejected=0
        for k,x in ar.items():
            y=br[k]
            if x['gap_percent'] is None or y['gap_percent'] is None:continue
            h=(x['host_id'],x['resource_cohort'])
            if not x['host_verified'] or not y['host_verified'] or 'unknown' in h or h!=(y['host_id'],y['resource_cohort']):rejected+=1;continue
            buckets[h].append(dict(case_id=x['case_id'],base_id=x['base_id'],gap_percent=x['gap_percent']-y['gap_percent']))
        for (h,cohort),matched in sorted(buckets.items()):
            cr=[]
            for case in sorted(set(x['case_id'] for x in matched)):
                xs=[x for x in matched if x['case_id']==case];cr.append(dict(case_id=case,base_id=xs[0]['base_id'],gap_percent=mean([x['gap_percent'] for x in xs])))
            pairs.append(dict(algorithm_a=a,algorithm_b=b,host_id=h,resource_cohort=cohort,common_feasible_gap_rows=len(matched),common_cases=len(cr),common_bases=len({x['base_id'] for x in cr}),case_equal_gap_difference_percentage_points=equal_mean(cr,'case_id'),base_equal_gap_difference_percentage_points=equal_mean(cr,'base_id'),excluded_cross_host_or_unknown_pairs_for_algorithm_pair=rejected))
        if not buckets:pairs.append(dict(algorithm_a=a,algorithm_b=b,host_id=None,resource_cohort=None,common_feasible_gap_rows=0,excluded_cross_host_or_unknown_pairs_for_algorithm_pair=rejected))
    return rows,dict(schema='urp-cvrplib-host-summary-v1',cohort=plan['cohort'],notes=['Pooled quality is descriptive heterogeneous-hardware execution, not equal-hardware benchmarking.','Timing is only summarized within a verified host/resource cohort; no pooled speed ranks.','Seed assignment is confounded with host; same-host case+seed pairs only.'],groups=groups,ownership_progress=ownership,pairwise_by_host_resource=pairs,unexpected_results=old['unexpected_results'])
def main():
    p=argparse.ArgumentParser()
    for k in ('plan','cases','distribution','assignment','out'):p.add_argument('--'+k,required=True,type=Path)
    p.add_argument('--runs',required=True,type=Path,nargs='+')
    a=p.parse_args();plan=json.loads(a.plan.read_text());assignment=json.loads(a.assignment.read_text())
    if sha(a.cases)!=plan['case_manifest_sha256']:raise ValueError('Case manifest bytes differ from frozen plan')
    if assignment.get('canonical_plan_sha256')!=sha(a.plan):raise ValueError('Assignment belongs to a different plan')
    rows,s=aggregate_hosts(plan,json.loads(a.cases.read_text()),json.loads(a.distribution.read_text()),a.runs,assignment);a.out.mkdir(parents=True,exist_ok=True)
    with (a.out/'runs.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (a.out/'summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
