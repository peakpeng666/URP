"""Synthetic 100-node fixtures; never research results. No real instance data included."""
import json
from pathlib import Path
from backend import public_routes as p
from backend.store import canonical, sha


def fixture(root, format=p.PUBLIC_FORMAT):
    portfolio = format == p.PORTFOLIO_FORMAT
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    def write(name, value):
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical(value)+'\n')
    text = 'c101\n\nVEHICLE\nNUMBER     CAPACITY\n3 100\n\nCUSTOMER\n'
    text += ''.join(f'{i} {i} 0 {int(i>0)} 0 1000 0\n' for i in range(101))
    (root/'inputs').mkdir()
    (root/'inputs/c101.txt').write_text(text)
    nodes = [dict(id=i,x=i,y=0,demand=int(i>0),ready=0,due=1000,service=0) for i in range(101)]
    parsed = dict(id='c101',family='C1',vehicles=3,capacity=100,nodes=nodes)
    manifest = [dict(name='c101.txt',sha256=sha(text.encode()),bytes=len(text.encode()),
        semantic_sha256=sha(canonical(parsed).encode()),encoded_sha256=p.encoded_hash(nodes),
        family='C1',n_customers=100,vehicle_limit=3,capacity=100,depot_due=1000)]
    write('protocol/input_manifest.json',manifest)
    protocol = {'study_id':'SOLVER_PORTFOLIO_HEADROOM_ARCHIVED100_V1' if portfolio else 'ARCHIVED_SOLOMON100_DISTANCE_ONLY_FIXED_V1',
        'encoding' if portfolio else 'integer_encoding':{'scale':1000000},'fixture':'synthetic test only'}
    write('protocol/protocol.json',protocol)
    write('evidence/environment.json',{'ortools_version' if portfolio else 'ortools':'synthetic-no-solver'})
    path = root/'source/checker.py'
    path.parent.mkdir()
    path.write_bytes(Path(p.__file__).with_name('archived_solomon_checker.py').read_bytes())
    geometry = sha(canonical({'depot':[0,0],'customers':[[i,0] for i in range(1,101)]}).encode())
    if portfolio:
        write('protocol/shared_geometry.json',{'geometry_sha256':[{'sha256':geometry,'instances':['c101'],'n':1}]})
    requests, raw, evaluated, checks = [], [], [], []
    configs = list(p.CONFIGS) if portfolio else [250,1000]
    original = {'fleet':3,'capacity':100,'nodes':{n['id']:[n[k] for k in ('x','y','demand','ready','due','service')] for n in nodes}}
    for sequence, config in enumerate(configs):
        ms = p.CONFIGS[config][0] if portfolio else config
        run_id = f'c101__{config}' if portfolio else f'c101__{ms}ms'
        request = dict(sequence=sequence,instance='c101',family='C1',budget_ms=ms,seed=1,run_id=run_id)
        if portfolio:
            request.update(config_id=config,strategy=p.CONFIGS[config][1],role='synthetic')
        requests.append(request)
        (root/f'protocol/parameters_{config if portfolio else str(ms)+"ms"}.textproto').write_text('synthetic no solver\n')
        routes = [{'vehicle':2,'nodes':[0,*range(1,101),0],'encoded_cumul_ranges':[]}]
        audit = p.check(original,routes)
        obj, arcs = p.objective_check(original,routes)
        row = {**request,'assignment_returned':True,'ortools_status':1,'ortools_status_name':'ROUTING_SUCCESS',
            'routes':routes,'objective_integer':obj,'outcome':'SUCCESS' if portfolio else 'ASSIGNMENT_UNCHECKED',
            'vehicles_used':1,'solve_wall_s':0.3,'solve_cpu_s':0.2,'model_wall_s':0.01,'model_cpu_s':0.005,
            'total_wall_s':0.31,'total_cpu_s':0.205,'first_solution':None}
        if portfolio:
            audit.update(independent_objective_integer=obj,reported_objective_integer=obj,
                rounding_error=abs(obj/1e6-audit['distance']),rounding_bound=0.5*arcs/1e6+1e-9,arc_count=arcs)
            row['check_summary'] = {k:v for k,v in audit.items() if k!='route_audits'}
            checks.append({'run_id':run_id,**audit})
            evaluated.append(dict(row))
        else:
            evaluated.append({**row,'outcome':'SUCCESS','continuous_check':audit,'original_distance':audit['distance'],
                'encoding_cost_error':obj/1e6-audit['distance'],'encoding_cost_error_bound':0.5*arcs/1e6})
        raw.append(row)
    write('protocol/requests.json',requests)
    write('reports/evaluated_results.json',evaluated)
    (root/'raw').mkdir()
    (root/'raw/results.jsonl').write_text(''.join(canonical(r)+'\n' for r in raw))
    if portfolio:
        (root/'raw/continuous_checks.jsonl').write_text(''.join(canonical(r)+'\n' for r in checks))
    write('evidence/verification.json',{'request_count':len(raw),'raw_count':len(raw),
        'checker_success_count' if portfolio else 'checker_passed_count':len(raw)})
    frozen = [f for d in ('protocol','source') for f in (root/d).glob('*') if f.name!='freeze.json']
    frozen += [root/'evidence/environment.json']
    write('protocol/freeze.json',{'solver_calls_before_freeze':0,'sha256':{str(f.relative_to(root)):sha(f.read_bytes()) for f in frozen}})
    return sha((root/'protocol/protocol.json').read_bytes())


def load_blobs(root):
    return ({str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file() and 'inputs' not in f.parts},
            {'c101.txt':(root/'inputs/c101.txt').read_bytes()})
