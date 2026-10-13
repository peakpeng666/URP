"""Freeze, run, analyze and replay a distinct fresh-dev scale/budget study."""
import argparse
from collections import Counter,defaultdict
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import shutil
import statistics
import time
from urp_cvrp.instance import load_instance
from urp_cvrp.generate import generate_instance
from urp_cvrp.checker import check_solution
from mature_pyvrp_v1.run_experiment import dependency_state_ok
from scale_budget_v1.runtime import run

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')


def generate(config):
    data=HERE/'data/dev'
    data.mkdir(parents=True,exist_ok=False)
    entries=[];index=0
    for family in config['families']:
        for n in config['customer_counts']:
            for replicate in range(config['instances_per_cell']):
                seed=config['generation_seed_base']+index;index+=1
                if 2026101400<=seed<=2026101499:raise ValueError('reserved holdout namespace')
                instance=generate_instance(n,family,seed,config['capacity'])
                name=instance.instance_id+'.json';write(data/name,instance.to_dict())
                entries.append({'instance_id':instance.instance_id,'file':name,'sha256':instance.sha256,
                                'family':family,'n_customers':n,'generation_seed':seed,'replicate':replicate})
    manifest={'schema_version':'scale-budget-dev-manifest-v1','split':'dev',
      'seed_namespace':f"{config['generation_seed_base']}..{config['generation_seed_base']+index-1}",
      'instances':entries,'generator':'unchanged urp_cvrp.generate.generate_instance; new wrapper avoids old hardcoded manifest namespace',
      'final_holdout_status':'not_read_not_generated_not_evaluated'}
    write(data/'manifest.json',manifest)
    return manifest


def instances():
    manifest=read(HERE/'data/dev/manifest.json')
    if manifest['split']!='dev':raise ValueError('dev only')
    result=[]
    for e in manifest['instances']:
        if Path(e['file']).name!=e['file']:raise ValueError('local basename only')
        instance=load_instance(HERE/'data/dev'/e['file'])
        if instance.split!='dev' or instance.sha256!=e['sha256']:raise ValueError('input mismatch')
        result.append(instance)
    return result


def evaluate(instance,method,seed,profile,config,index):
    run_config={**config,**config['profiles'][profile]}
    raw=run(instance,method,seed,run_config)
    out=raw.get('output')
    start_cpu,start_wall=time.process_time(),time.perf_counter()
    check=check_solution(instance,out)
    checker_cpu,checker_wall=time.process_time()-start_cpu,time.perf_counter()-start_wall
    accepted=raw['status']=='returned' and check.accepted
    cpu=raw.get('solver_cpu_seconds')
    conformant=cpu is not None and cpu<=run_config['cpu_budget_seconds'] and raw['process_wall_seconds']<=run_config['wall_budget_seconds']
    return {'call_index':index,'instance_id':instance.instance_id,'instance_sha256':instance.sha256,
        'family':instance.family,'n_customers':instance.n_customers,'split':'dev','algorithm':method,'solver_seed':seed,'profile':profile,
        **raw,'accepted':accepted,'budget_conformant':conformant,'scoreable':accepted and conformant,
        'recomputed_cost':check.recomputed_cost if accepted else None,'checker_errors':list(check.errors),
        'checker_cpu_seconds':checker_cpu,'checker_wall_seconds':checker_wall,
        'routes':out.get('routes') if isinstance(out,dict) else None,
        'search':out.get('search',{}) if isinstance(out,dict) else {},
        'solver_cpu_overrun_seconds':max(0,cpu-run_config['cpu_budget_seconds']) if cpu is not None else None}


def describe(xs):
    return {'mean':statistics.mean(xs),'median':statistics.median(xs),'minimum':min(xs),'maximum':max(xs)} if xs else None


def paired(rows,left_method,right_method,left_profile,right_profile,seeds):
    index={(r['instance_id'],r['algorithm'],r['profile'],r['solver_seed']):r for r in rows}
    pairs=[];missing=[]
    for instance_id in sorted({r['instance_id'] for r in rows}):
        left=[index[(instance_id,left_method,left_profile,s)] for s in seeds]
        right=[index[(instance_id,right_method,right_profile,s)] for s in seeds]
        if not all(r['scoreable'] for r in left+right):missing.append(instance_id);continue
        a,b=statistics.mean(r['recomputed_cost'] for r in left),statistics.mean(r['recomputed_cost'] for r in right)
        pairs.append({'instance_id':instance_id,'family':left[0]['family'],'n_customers':left[0]['n_customers'],
            'baseline_mean_cost':a,'candidate_mean_cost':b,'reduction_percent':100*(a-b)/a if a else 0})
    vals=[r['reduction_percent'] for r in pairs];groups=defaultdict(list)
    for r in pairs:groups[f"{r['family']}_n{r['n_customers']}"].append(r['reduction_percent'])
    return {'paired_instances':len(pairs),'excluded_incomplete_or_nonconformant_instances':missing,
      'reduction_percent':describe(vals),'wins':sum(x>1e-7 for x in vals),'ties':sum(abs(x)<=1e-7 for x in vals),'losses':sum(x<-1e-7 for x in vals),
      'strata':{k:{'instances':len(v),**describe(v)} for k,v in sorted(groups.items())},'instances':pairs}


def summarize(rows,config):
    groups=defaultdict(list)
    for row in rows:groups[row['profile']+'__'+row['algorithm']].append(row)
    algorithms={}
    for name,rs in groups.items():
        algorithms[name]={'calls':len(rs),'accepted':sum(r['accepted'] for r in rs),'in_budget_accepted':sum(r['scoreable'] for r in rs),
          'status_counts':dict(Counter(r['status'] for r in rs)),'termination_counts':dict(Counter(r['search'].get('termination','constructor_or_failure') for r in rs)),
          'solver_cpu_seconds':describe([r['solver_cpu_seconds'] for r in rs if r.get('solver_cpu_seconds') is not None]),
          'complete_child_cpu_seconds':describe([r['child_total_cpu_seconds'] for r in rs]),
          'total_wall_seconds':describe([r['total_wall_seconds'] for r in rs]),'peak_rss_kib':describe([r['child_peak_rss_kib'] for r in rs]),
          'max_cpu_overrun_seconds':max((r['solver_cpu_overrun_seconds'] or 0) for r in rs)}
    comparisons={}
    for profile in config['profiles']:
        for left,right in (('parallel_savings','multistart_vnd'),('multistart_vnd','pyvrp_ils_s1e6')):
            comparisons[f'{profile}__{right}_vs_{left}']=paired(rows,left,right,profile,profile,config['solver_seeds'])
    for method in config['algorithms']:
        comparisons[f'{method}__cpu100_vs_cpu025']=paired(rows,method,method,'cpu025','cpu100',config['solver_seeds'])
    return {'calls':len(rows),'base_instances':len({r['instance_id'] for r in rows}),'accepted':sum(r['accepted'] for r in rows),
      'in_budget_accepted':sum(r['scoreable'] for r in rows),'algorithms':algorithms,'comparisons':comparisons,
      'qualification':'Development descriptive only; seeds/budgets/replays are not additional independent instances; failure exclusions explicitly listed.'}


def sources():
    out=list((ROOT/'urp_cvrp').glob('*.py'))+list(HERE.glob('*.py'))+[HERE/'protocol.json',HERE/'PROTOCOL.md']
    out += [ROOT/'local_search_v2/solvers.py',ROOT/'local_search_v2/__init__.py']
    out += [ROOT/'mature_pyvrp_v1'/n for n in ('__init__.py','adapter.py','run_experiment.py','runtime.py','dependency_provenance.json','requirements.lock.txt')]
    return sorted(out)


def execute(folder):
    folder=Path(folder).resolve()
    if not folder.is_relative_to(HERE):raise ValueError('stay in subtree')
    config=read(HERE/'protocol.json')
    if not dependency_state_ok():raise ValueError('dependency hashes changed')
    ins=instances();by_id={i.instance_id:i for i in ins}
    folder.mkdir(parents=True,exist_ok=False)
    order=[(i.instance_id,s,p) for i in ins for s in config['solver_seeds'] for p in config['profiles']]
    rng=random.Random(config['schedule_seed']);rng.shuffle(order);calls=[]
    for instance_id,seed,profile in order:
        methods=config['algorithms'][:];rng.shuffle(methods)
        calls += [{'instance_id':instance_id,'seed':seed,'profile':profile,'algorithm':m} for m in methods]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sources()}
    previous=[]
    for stage in ('local_search_v1','local_search_v2','mature_pyvrp_v1'):
        previous += list((ROOT/stage).glob('*.py'))
        for pattern in ('*.json','*.jsonl','*.csv'):previous += list((ROOT/stage/'runs').rglob(pattern))
    previous += list((ROOT/'data/dev').glob('*.json'))+list((ROOT/'results').glob('*.*'))
    old={str(p.relative_to(ROOT)):sha(p) for p in previous if p.is_file()}
    freeze={'frozen_utc':utc(),'config':config,'calls':calls,'source_hashes':hashes,'prior_hashes':old,
       'instance_sha256':{i.instance_id:i.sha256 for i in ins},'manifest_sha256':sha(HERE/'data/dev/manifest.json'),
       'python':platform.python_version(),'os':platform.platform(),'final_holdout_status':'not_read_not_generated_not_evaluated',
       'cpu_model':next((s.split(':',1)[1].strip() for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name')),'unknown')}
    for p in sources():
        target=folder/'source_snapshot'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    write(folder/'freeze.json',freeze)
    rows=[];wall=time.perf_counter();cpu=time.process_time();started=utc()
    with (folder/'raw.jsonl').open('x') as log:
        for idx,call in enumerate(calls):
            row=evaluate(by_id[call['instance_id']],call['algorithm'],call['seed'],call['profile'],config,idx)
            rows.append(row);log.write(json.dumps(row,allow_nan=False)+'\n');log.flush()
            if (idx+1)%36==0:print(f"{idx+1}/{len(calls)} recorded; {sum(x['accepted'] for x in rows)} feasible; {sum(x['scoreable'] for x in rows)} in-budget",flush=True)
    elapsed=time.perf_counter()-wall;parent=time.process_time()-cpu;children=sum(r['child_total_cpu_seconds'] for r in rows)
    result={'started_utc':started,'finished_utc':utc(),'config':config,'runs':rows,'summary':summarize(rows,config),
      'accounting':{'batch_wall_seconds':elapsed,'batch_parent_cpu_seconds':parent,'complete_child_cpu_seconds':children,
        'batch_parent_plus_child_cpu_seconds':parent+children,'solver_cpu_seconds':sum(r.get('solver_cpu_seconds',0) for r in rows),
        'scope':'batch loop/raw-log flushes; excludes setup/tests/freezing/finalwrites/replay/analysis/assistant labor','experimental_model_api_calls':0},
      'source_unchanged':all(sha(ROOT/p)==h for p,h in hashes.items()),
      'prior_artifacts_unchanged':all(sha(ROOT/p)==h for p,h in old.items()),'installed_pyvrp_hashes_match':dependency_state_ok()}
    write(folder/'results.json',result);write(folder/'summary.json',result['summary'])
    with (folder/'raw.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(v,allow_nan=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})
    print(json.dumps({'calls':len(rows),'accepted':result['summary']['accepted'],'in_budget':result['summary']['in_budget_accepted'],'accounting':result['accounting']},indent=2))


def verify(folder):
    folder=Path(folder).resolve();result=read(folder/'results.json');freeze=read(folder/'freeze.json')
    if (folder/'verification.json').exists() or (folder/'replay_raw.jsonl').exists():raise FileExistsError('no overwrites')
    if not dependency_state_ok() or not all(sha(ROOT/p)==h for p,h in freeze['source_hashes'].items()):raise ValueError('source/dependency mismatch')
    ins={i.instance_id:i for i in instances()};checks=[]
    for row in result['runs']:
        c=check_solution(ins[row['instance_id']],row['output'])
        checks.append(c.accepted==row['accepted'] and (not c.accepted or c.recomputed_cost==row['recomputed_cost']))
    wall=time.perf_counter();cpu=time.process_time();replays=[];matches=[]
    with (folder/'replay_raw.jsonl').open('x') as log:
        for row in result['runs']:
            repeat=evaluate(ins[row['instance_id']],row['algorithm'],row['solver_seed'],row['profile'],result['config'],row['call_index'])
            replays.append(repeat);log.write(json.dumps(repeat,allow_nan=False)+'\n');log.flush()
            matches.append({'call_index':row['call_index'],'same_routes':repeat['routes']==row['routes'],
              'same_cost':repeat['recomputed_cost']==row['recomputed_cost'],'primary_accepted':row['accepted'],'replay_accepted':repeat['accepted'],
              'cost_difference_replay_minus_primary':repeat['recomputed_cost']-row['recomputed_cost'] if repeat['accepted'] and row['accepted'] else None})
    elapsed=time.perf_counter()-wall;parent=time.process_time()-cpu
    with (folder/'raw.csv').open(newline='') as f:csvrows=list(csv.DictReader(f))
    csv_ok=len(csvrows)==len(result['runs']) and all(
      text[k]==(json.dumps(v,allow_nan=False) if isinstance(v,(list,dict)) else '' if v is None else str(v))
      for row,text in zip(result['runs'],csvrows) for k,v in row.items())
    schedule_ok=len(result['runs'])==len(freeze['calls']) and all(row['call_index']==idx and all(row[k]==call[q] for k,q in [('instance_id','instance_id'),('algorithm','algorithm'),('solver_seed','seed'),('profile','profile')]) for idx,(row,call) in enumerate(zip(result['runs'],freeze['calls'])))
    out={'verified_utc':utc(),'persisted_routes_checked':len(checks),'persisted_checks_match':sum(checks),
      'replay_calls':len(replays),'replay_feasible':sum(r['accepted'] for r in replays),'replay_in_budget':sum(r['scoreable'] for r in replays),
      'exact_route_and_cost_replays':sum(r['same_routes'] and r['same_cost'] for r in matches),
      'same_cost_replays':sum(r['same_cost'] for r in matches),'matches':matches,'replay_summary':summarize(replays,result['config']),
      'raw_jsonl_matches_json':[json.loads(x) for x in (folder/'raw.jsonl').read_text().splitlines()]==result['runs'],
      'raw_csv_matches_json':csv_ok,'schedule_matches_freeze':schedule_ok,
      'summary_recomputed_matches':summarize(result['runs'],result['config'])==result['summary'],
      'source_and_snapshot_hashes_match':all(sha(ROOT/p)==h and sha(folder/'source_snapshot'/p)==h for p,h in freeze['source_hashes'].items()),
      'prior_hashes_match':all(sha(ROOT/p)==h for p,h in freeze['prior_hashes'].items()),'installed_pyvrp_hashes_match':dependency_state_ok(),
      'accounting':{'wall_seconds':elapsed,'parent_cpu_seconds':parent,'complete_child_cpu_seconds':sum(r['child_total_cpu_seconds'] for r in replays)},
      'replay_outputs':'All full raw records and routes preserved in replay_raw.jsonl; no primary replacement'}
    write(folder/'verification.json',out)
    print(json.dumps({k:v for k,v in out.items() if k not in ('matches','replay_summary')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['generate','run','verify']);parser.add_argument('--output')
    args=parser.parse_args()
    if args.action=='generate':generate(read(HERE/'protocol.json'))
    elif args.action=='run':execute(args.output)
    else:verify(args.output)
