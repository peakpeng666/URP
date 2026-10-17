"""Aggregate fixed-plan runs without dropping failed/unstarted keys. Standard library only."""
import argparse,csv,hashlib,itertools,json,math,statistics
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path

def mean(xs): return statistics.mean(xs) if xs else None
def finite_number(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:return False
def key(r):
    if not isinstance(r,dict) or any(not isinstance(r.get(k),str) or not r[k] for k in ('case_id','algorithm')) or type(r.get('seed')) is not int or r['seed']<0 or not finite_number(r.get('budget_seconds')) or not 0<r['budget_seconds']<=60:
        raise ValueError('Invalid result/plan key: explicit case, algorithm, integer seed and positive finite budget required')
    return (r['case_id'],r['algorithm'],r['seed'],r['budget_seconds'])
def planned_keys(plan):
    for axis in ('case_ids','algorithms','seeds'):
        values=plan.get(axis)
        if not isinstance(values,list) or not values:raise ValueError('Plan axes must be nonempty lists')
        if axis=='seeds':valid=all(type(x) is int and x>=0 for x in values)
        else:valid=all(isinstance(x,str) and x for x in values)
        if not valid or len(set(values))!=len(values):raise ValueError('Duplicate or invalid plan axis: '+axis)
    budget=plan.get('budget_seconds')
    if not finite_number(budget) or not 0<budget<=60:raise ValueError('Invalid planned budget')
    expected={(c,a,s,budget) for c,a,s in itertools.product(plan['case_ids'],plan['algorithms'],plan['seeds'])}
    if 'planned_keys' in plan and (type(plan['planned_keys']) is not int or plan['planned_keys']!=len(expected)):
        raise ValueError('Declared planned denominator differs from Cartesian plan')
    if 'schedule' in plan:
        if not isinstance(plan['schedule'],list):raise ValueError('Schedule must be a list')
        scheduled=[key(r) for r in plan['schedule']]
        if len(scheduled)!=len(expected) or set(scheduled)!=expected:raise ValueError('Schedule must contain each planned key exactly once')
    return expected
def indexed_cases(items,label):
    rows={}
    for row in items:
        case_id=row['case_id']
        if case_id in rows:raise ValueError('Duplicate '+label+' case ID: '+case_id)
        rows[case_id]=row
    return rows
def checked_cost(check):
    return isinstance(check,dict) and all(check.get(k) is True for k in ('valid','feasible','reported_cost_checked','reported_cost_matches')) and check.get('errors')==[] and type(check.get('cost')) is int and finite_number(check['cost']) and check['cost']>=0
def equal_mean(rows, group):
    buckets=defaultdict(list)
    for r in rows:
        if r['gap_percent'] is not None: buckets[r[group]].append(r['gap_percent'])
    return mean([mean(v) for v in buckets.values()])
def summarize(rows):
    valid=[r for r in rows if r['feasible']]
    percase=defaultdict(list)
    for r in rows:
        if r['gap_percent'] is not None: percase[r['case_id']].append(r['gap_percent'])
    caserows=[dict(case_id=c,base_id=next(r['base_id'] for r in rows if r['case_id']==c),gap_percent=mean(v)) for c,v in percase.items()]
    cpu=[r['cpu_seconds'] for r in rows if r['started'] and r['cpu_seconds'] is not None]
    return dict(planned=len(rows),started=sum(r['started'] for r in rows),not_started=sum(not r['started'] for r in rows),feasible=len(valid),failed_started=sum(r['started'] and not r['feasible'] for r in rows),feasible_rate_of_planned=len(valid)/len(rows) if rows else None,status_counts=dict(Counter(r['status'] for r in rows)),gap_rows=sum(r['gap_percent'] is not None for r in rows),gap_status_counts=dict(Counter(r['gap_status'] for r in rows)),quality_case_count=len(caserows),quality_base_count=len(set(r['base_id'] for r in caserows)),case_equal_gap_percent=equal_mean(caserows,'case_id'),base_equal_gap_percent=equal_mean(caserows,'base_id'),cpu_seconds_mean_started=mean(cpu),cpu_rows_started=len(cpu))
def aggregate(plan,cases,distribution,runroot,plan_sha256=None):
    planned_keys(plan)
    cm=indexed_cases(cases['cases'],'instance'); dm={k:v['customer_distribution'] for k,v in indexed_cases(distribution['cases'],'distribution').items()}; found={}; extras=[]
    if any(c not in cm for c in plan['case_ids']):raise ValueError('Plan references a case absent from the case manifest')
    roots=runroot if isinstance(runroot,(list,tuple)) else [runroot]
    paths=sorted({p.resolve() for root in roots for p in root.rglob('result.json')})
    for p in paths:
        r=json.loads(p.read_text()); k=key(r)
        if k in found: raise ValueError(f'Duplicate attempt key {k}; select predeclared attempt in separate directory, never best-of-retries')
        found[k]=(p,r)
    rows=[]
    for c,a,s in itertools.product(plan['case_ids'],plan['algorithms'],plan['seeds']):
        case=cm[c]; k=(c,a,s,plan['budget_seconds']); item=found.pop(k,None)
        row=dict(case_id=c,base_id=case['base_id'],algorithm=a,seed=s,budget_seconds=plan['budget_seconds'],size_stratum=case['size_stratum'],source_family=case['source_family'],contract_id=case['contract']['id'],distribution=dm.get(c,distribution['family_metadata'].get(case['source_family'],{}).get('customer_distribution','unknown')),started=item is not None,status='NOT_STARTED',feasible=False,cost=None,gap_percent=None,gap_status='NOT_ELIGIBLE',cpu_seconds=None,measurement_errors=[],result_path=None,reference_review_required=False)
        if item:
            p,r=item; ep=p.with_name('evaluation.json'); row.update(status=r.get('status','MISSING_STATUS'),result_path=str(p))
            cpu=r.get('cpu_seconds')
            if finite_number(cpu) and cpu>=0:row['cpu_seconds']=cpu
            elif cpu is not None:row['measurement_errors'].append('invalid cpu_seconds')
            if r.get('schema')!='urp-cvrplib-result-v1' or type(r.get('feasible')) is not bool or not isinstance(r.get('status'),str) or not r['status']:
                row['status']='RESULT_SCHEMA_INVALID'
            elif r.get('purpose')!='formal_baseline' or r.get('protocol_sha256')!=plan['protocol_sha256'] or r.get('instance_sha256')!=case['instance_sha256'] or r.get('case_manifest_sha256')!=plan['case_manifest_sha256'] or (plan_sha256 is not None and r.get('plan_sha256')!=plan_sha256) or (plan.get('solver_source_sha256') is not None and r.get('solver_source_sha256') != plan['solver_source_sha256']) or ('solver_source_end_sha256' in r and r['solver_source_end_sha256']!=r.get('solver_source_sha256')):
                row['status']='METADATA_MISMATCH'
            elif not ep.exists(): row['status']='CHECKER_MISSING'
            else:
                try:e=json.loads(ep.read_text())
                except (OSError,ValueError):e=None
                if not isinstance(e,dict):row['status']='CHECKER_INVALID'
                elif e.get('result_sha256')!=hashlib.sha256(p.read_bytes()).hexdigest(): row['status']='CHECKER_HASH_MISMATCH'
                elif r['feasible'] and r.get('status') in ('OK','TIMEOUT_WITH_FEASIBLE_INCUMBENT') and checked_cost(e.get('candidate_check')) and type(r.get('cost')) is int and r['cost']==e['candidate_check']['cost']:
                    row.update(feasible=True,cost=e['candidate_check']['cost'])
                    if e.get('eligible_for_gap') is True:
                        reference=e.get('reference_check')
                        if not checked_cost(reference) or reference['cost']==0:row['gap_status']='REFERENCE_CHECKER_REJECTED'
                        else:
                            gap=float(Fraction(100*(row['cost']-reference['cost']),reference['cost']))
                            if not finite_number(e.get('gap_percent')) or not math.isclose(e['gap_percent'],gap,rel_tol=1e-12,abs_tol=1e-12):row['gap_status']='GAP_MISMATCH'
                            else:row.update(gap_percent=gap,gap_status='CHECKED',reference_review_required=gap<0 or e.get('reference_review_required') is True)
                elif r['feasible']: row['status']='CHECKER_REJECTED'
        rows.append(row)
    extras=[dict(key=list(k),path=str(v[0])) for k,v in found.items()]
    groups={}
    for axis in ('overall','size_stratum','distribution','source_family','contract_id'):
        buckets=defaultdict(list)
        for r in rows: buckets[(r['algorithm'],'all' if axis=='overall' else r[axis])].append(r)
        groups[axis]=[dict(algorithm=a,group=g,**summarize(v)) for (a,g),v in sorted(buckets.items())]
    pairs=[]
    for a,b in itertools.combinations(plan['algorithms'],2):
        ar={(r['case_id'],r['seed']):r for r in rows if r['algorithm']==a}; br={(r['case_id'],r['seed']):r for r in rows if r['algorithm']==b}; matched=[]
        for k in ar:
            x,y=ar[k],br[k]
            if x['gap_percent'] is not None and y['gap_percent'] is not None: matched.append(dict(case_id=x['case_id'],base_id=x['base_id'],gap_percent=x['gap_percent']-y['gap_percent']))
        cr=[]
        for case in sorted(set(x['case_id'] for x in matched)):
            xs=[x for x in matched if x['case_id']==case];cr.append(dict(case_id=case,base_id=xs[0]['base_id'],gap_percent=mean([x['gap_percent'] for x in xs])))
        pairs.append(dict(algorithm_a=a,algorithm_b=b,planned_paired_rows=len(ar),common_feasible_gap_rows=len(matched),common_cases=len(cr),common_bases=len(set(x['base_id'] for x in cr)),case_equal_gap_difference_percentage_points=equal_mean(cr,'case_id'),base_equal_gap_difference_percentage_points=equal_mean(cr,'base_id')))
    per_case=[]
    for c,a in itertools.product(plan['case_ids'],plan['algorithms']):
        rr=[r for r in rows if r['case_id']==c and r['algorithm']==a]; gg=[r['gap_percent'] for r in rr if r['gap_percent'] is not None]
        per_case.append(dict(case_id=c,algorithm=a,**summarize(rr),gap_stddev=statistics.stdev(gg) if len(gg)>1 else None,best_of_repeats_gap=min(gg) if gg else None,best_of_repeats_budget_note='Selection across all planned repeats; not single-run performance'))
    return rows,dict(schema='urp-cvrplib-summary-v1',cohort=plan['cohort'],denominator_policy='All planned keys retained; quality conditional on independently checked feasibility; pairwise matched case+seed',groups=groups,per_case=per_case,pairwise=pairs,unexpected_results=extras)
def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True,type=Path);p.add_argument('--cases',required=True,type=Path);p.add_argument('--distribution',required=True,type=Path);p.add_argument('--runs',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    plan=json.loads(a.plan.read_text())
    if hashlib.sha256(a.cases.read_bytes()).hexdigest()!=plan['case_manifest_sha256']:raise ValueError('Case manifest bytes differ from frozen plan')
    rows,summary=aggregate(plan,json.loads(a.cases.read_text()),json.loads(a.distribution.read_text()),a.runs,hashlib.sha256(a.plan.read_bytes()).hexdigest())
    a.out.mkdir(parents=True,exist_ok=True)
    with (a.out/'runs.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (a.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
if __name__=='__main__': main()
