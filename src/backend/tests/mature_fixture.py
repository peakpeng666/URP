"""Tiny synthetic mature-v1 archive (2 inputs, 4 runs); not research evidence."""
import copy
import hashlib
import json
from pathlib import Path
from route_fixture import write_fixture


def write_mature_fixture(root):
    root=Path(root);legacy=write_fixture(root/'legacy');mature=root/'mature';mature.mkdir(parents=True,exist_ok=True)
    inputs=json.loads((legacy/'inputs.json').read_text())
    oldrows=[json.loads(l) for l in (legacy/'routes.jsonl').read_text().splitlines()]
    oracle=copy.deepcopy(oldrows[0]);oracle['method']='oracle_full';oracle['status']='optimal';oldrows.append(oracle)
    (legacy/'routes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in oldrows))
    oldmap=json.loads((legacy/'map_backend.json').read_text());oldmap['solutions']=oldrows;(legacy/'map_backend.json').write_text(json.dumps(oldmap))
    v=json.loads((legacy/'verification.json').read_text());v['record_count']=5;(legacy/'verification.json').write_text(json.dumps(v))
    for name in ['inputs.json','checker.py']:(mature/name).write_bytes((legacy/name).read_bytes())
    (mature/'reference').mkdir(exist_ok=True)
    for name in ['inputs.json','protocol.json','freeze.json','routes.jsonl']:(mature/'reference'/name).write_bytes((legacy/name).read_bytes())
    requests=[];results=[];evaluated=[]
    for item in inputs:
        found=item['id']=='fixture_possible'
        for budget in [250,1000]:
            request=dict(sequence=len(requests),instance=item['id'],budget_ms=budget,
                run_id=f"{item['id']}__{budget}ms",random_seed=0);requests.append(request)
            row={**request,'ortools_status':1 if found else 3,'ortools_status_name':'ROUTING_SUCCESS' if found else 'ROUTING_FAIL',
                'assignment_returned':found,'solve_wall_s':0,'solve_cpu_s':0,'model_wall_s':0,'model_cpu_s':0,
                'total_wall_s':0,'total_cpu_s':0,'routes':oldrows[0]['routes'] if found else None,
                'audit':oldrows[0]['audit'] if found else None,'outcome':'find' if found else 'no_solution_in_budget',
                'objective_integer':4000000 if found else None,'encoded_cumul_ranges':[] if found else None,'first_solution':None}
            results.append(row);evaluated.append({**row,'full_gap_original_percent':0 if found else None,'reference_oracle_full_feasible':found})
    (mature/'results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results))
    input_hash=hashlib.sha256((mature/'inputs.json').read_bytes()).hexdigest()
    objects={'protocol.json':{'study_id':'SYNTHETIC_MATURE_FIXTURE','budgets_ms':[250,1000],
        'solver':'Synthetic fixture only','integer_encoding':{'scale':1000000}},
        'requests.json':requests,'evaluated_results.json':evaluated,'environment.json':{'ortools':'TEST_ONLY'},
        'encoded_inputs.json':{'TEST_ONLY':True},'checker_tests.json':{'TEST_ONLY':True},
        'verification.json':{'passed':True,'records_checked':4,'returned_solutions_independently_replayed':2,'original_input_sha256':input_hash},
        'map_backend.json':{'schema':'vrptw-mature-solver-v1','synthetic_coordinates':True,
            'distance_time_units':'Arbitrary Euclidean units; speed1; not real latitude/longitude, road travel or traffic',
            'source_input_sha256':input_hash,'instances':[{'input':item,'reference_oracle_full_feasible':item['id']=='fixture_possible',
                'runs':[r for r in evaluated if r['instance']==item['id']]} for item in inputs]}}
    for name,obj in objects.items():(mature/name).write_text(json.dumps(obj))
    for budget in [250,1000]:(mature/f'parameters_{budget}ms.textproto').write_text('# INERT TEST PARAMETERS\n')
    frozen=['protocol.json','inputs.json','checker.py','requests.json','encoded_inputs.json','environment.json','parameters_250ms.textproto','parameters_1000ms.textproto']
    (mature/'freeze.json').write_text(json.dumps({'sha256':{n:hashlib.sha256((mature/n).read_bytes()).hexdigest() for n in frozen}}))
    return legacy,mature


def rewrite_results(source, mutate):
    """Mutate test-only non-frozen result evidence consistently across its three copies."""
    results=[json.loads(l) for l in (source/'results.jsonl').read_text().splitlines()]
    evaluated=json.loads((source/'evaluated_results.json').read_text());mapped=json.loads((source/'map_backend.json').read_text())
    for row in results:mutate(row)
    for row in evaluated:mutate(row)
    for item in mapped['instances']:
        for row in item['runs']:mutate(row)
    (source/'results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results))
    (source/'evaluated_results.json').write_text(json.dumps(evaluated));(source/'map_backend.json').write_text(json.dumps(mapped))
