"""Aggregate fixed-plan runs without dropping failed/unstarted keys. Standard library only."""
import argparse,csv,hashlib,itertools,json,statistics
from collections import Counter,defaultdict
from pathlib import Path

def mean(xs): return statistics.mean(xs) if xs else None
def key(r): return (r['case_id'],r['algorithm'],r['seed'],r['budget_seconds'])
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
    return dict(planned=len(rows),started=sum(r['started'] for r in rows),not_started=sum(not r['started'] for r in rows),feasible=len(valid),failed_started=sum(r['started'] and not r['feasible'] for r in rows),feasible_rate_of_planned=len(valid)/len(rows) if rows else None,status_counts=dict(Counter(r['status'] for r in rows)),gap_rows=sum(r['gap_percent'] is not None for r in rows),quality_case_count=len(caserows),quality_base_count=len(set(r['base_id'] for r in caserows)),case_equal_gap_percent=equal_mean(caserows,'case_id'),base_equal_gap_percent=equal_mean(caserows,'base_id'),cpu_seconds_mean_started=mean([r['cpu_seconds'] for r in rows if r['cpu_seconds'] is not None]))
def aggregate(plan,cases,distribution,runroot):
    cm={c['case_id']:c for c in cases['cases']}; dm={c['case_id']:c['customer_distribution'] for c in distribution['cases']}; found={}; extras=[]
    roots=runroot if isinstance(runroot,(list,tuple)) else [runroot]
    paths=sorted({p.resolve() for root in roots for p in root.rglob('result.json')})
    for p in paths:
        r=json.loads(p.read_text()); k=key(r)
        if k in found: raise ValueError(f'Duplicate attempt key {k}; select predeclared attempt in separate directory, never best-of-retries')
        found[k]=(p,r)
    rows=[]
    for c,a,s in itertools.product(plan['case_ids'],plan['algorithms'],plan['seeds']):
        case=cm[c]; k=(c,a,s,plan['budget_seconds']); item=found.pop(k,None)
        row=dict(case_id=c,base_id=case['base_id'],algorithm=a,seed=s,budget_seconds=plan['budget_seconds'],size_stratum=case['size_stratum'],source_family=case['source_family'],contract_id=case['contract']['id'],distribution=dm.get(c,distribution['family_metadata'].get(case['source_family'],{}).get('customer_distribution','unknown')),started=item is not None,status='NOT_STARTED',feasible=False,cost=None,gap_percent=None,cpu_seconds=None,result_path=None,reference_review_required=False)
        if item:
            p,r=item; ep=p.with_name('evaluation.json'); row.update(status=r.get('status','MISSING_STATUS'),cpu_seconds=r.get('cpu_seconds'),result_path=str(p))
            if r.get('purpose')!='formal_baseline' or r.get('protocol_sha256')!=plan['protocol_sha256'] or r.get('instance_sha256')!=case['instance_sha256'] or r.get('case_manifest_sha256')!=plan['case_manifest_sha256'] or (plan.get('solver_source_sha256') is not None and r.get('solver_source_sha256') != plan['solver_source_sha256']):
                row['status']='METADATA_MISMATCH'
            elif not ep.exists(): row['status']='CHECKER_MISSING'
            else:
                e=json.loads(ep.read_text())
                if e.get('result_sha256')!=hashlib.sha256(p.read_bytes()).hexdigest(): row['status']='CHECKER_HASH_MISMATCH'
                elif r.get('feasible') and r.get('status') in ('OK','TIMEOUT_WITH_FEASIBLE_INCUMBENT') and e.get('candidate_check',{}).get('valid') and e.get('candidate_check',{}).get('reported_cost_checked'):
                    row.update(feasible=True,cost=e['candidate_check'].get('cost'),gap_percent=e.get('gap_percent') if e.get('eligible_for_gap') else None,reference_review_required=e.get('reference_review_required',False))
                elif r.get('feasible'): row['status']='CHECKER_REJECTED'
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
    rows,summary=aggregate(json.loads(a.plan.read_text()),json.loads(a.cases.read_text()),json.loads(a.distribution.read_text()),a.runs)
    a.out.mkdir(parents=True,exist_ok=True)
    with (a.out/'runs.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (a.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__': main()
