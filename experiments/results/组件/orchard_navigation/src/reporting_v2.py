"""Post-run semantic reporting correction; does not change frozen solver or raw data.
An unreachable query has no optimal path cost: null/null is classification agreement.
"""
from __future__ import annotations
import copy,hashlib,json,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
    source=ROOT/'results/main';out=ROOT/'results/reporting_v2';out.mkdir(exist_ok=False)
    old=load(source/'viewer_data.json');view=copy.deepcopy(old)
    for p in view['paired_queries']:
        a=p['algorithms']['astar'];d=p['algorithms']['dijkstra']
        p['same_classification']=a['status']==d['status']
        p['both_correctly_unreachable']=(not p['expected_reachable'] and a['status']==d['status']=='unreachable' and a['validation_failures']==d['validation_failures']==0)
        if not p['expected_reachable']:p['same_optimal_cost']=None
    s=view['summary'];s.pop('all_paired_costs_agree')
    reach=[p for p in view['paired_queries'] if p['expected_reachable']];unreach=[p for p in view['paired_queries'] if not p['expected_reachable']]
    s['reachable_cost_agreement_count']=sum(p['same_optimal_cost'] is True for p in reach)
    s['reachable_optimal_costs_all_agree']=all(p['same_optimal_cost'] is True for p in reach)
    s['unreachable_classification_agreement_count']=sum(p['both_correctly_unreachable'] for p in unreach)
    s['unreachable_classifications_all_correct']=all(p['both_correctly_unreachable'] for p in unreach)
    s['cpu_metric']='end-to-end plan(raw_map,query,algorithm), including input checks, clearance preprocessing, graph search and path reconstruction'
    s['search_only_cpu_measured']=False;s['preprocessing_cpu_measured_separately']=False
    s['reporting_note']='Reporting-only correction: unreachable has no optimal path cost; original mechanical null/null equality was not numeric cost evidence. All numeric timing/work metrics and raw paths unchanged.'
    inputs=[source/'viewer_data.json',source/'summary.json',source/'paired_queries.json',source/'raw.jsonl',ROOT/'data/freeze.json',pathlib.Path(__file__).resolve()]
    view['reporting_revision']={'version':2,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':{str(p.relative_to(ROOT)):sha(p) for p in inputs}}
    s['reporting_revision']=view['reporting_revision']
    write(out/'paired_queries.json',view['paired_queries']);write(out/'summary.json',s)
    view['sources'] += [{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in [out/'summary.json',out/'paired_queries.json']]
    write(out/'viewer_data.json',view)
    allowed={'all_paired_costs_agree','reachable_cost_agreement_count','reachable_optimal_costs_all_agree','unreachable_classification_agreement_count','unreachable_classifications_all_correct','cpu_metric','search_only_cpu_measured','preprocessing_cpu_measured_separately','reporting_note','reporting_revision'}
    assert all(s[k]==v for k,v in old['summary'].items() if k not in allowed)
    for prior,current in zip(old['paired_queries'],view['paired_queries']):
        assert all(current[k]==v for k,v in prior.items() if k!='same_optimal_cost')
    assert view['runs']==old['runs'] and view['maps']==old['maps'] and view['queries']==old['queries']
    assert s['reachable_cost_agreement_count']==84 and s['unreachable_classification_agreement_count']==12
    write(out/'verification.json',{'passed':True,'raw_runs_inputs_and_numeric_metrics_unchanged':True,'reachable_cost_agreements':84,'correct_unreachable_agreements':12,'unreachable_cost_equality_is_null':True,'input_hashes':view['reporting_revision']['inputs']})
    print('Reporting projection verified:84 reachable equal optimal costs;12 correctly unreachable;all original measurements unchanged')
if __name__=='__main__':main()
