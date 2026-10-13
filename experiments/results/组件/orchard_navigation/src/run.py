from __future__ import annotations
import argparse,datetime,gc,hashlib,json,os,pathlib,platform,sys,time,traceback
from planners import plan
from validator import geometry_free,bfs_oracle,validate
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def check_freeze():
    f=load(ROOT/'data/freeze.json')
    for relative,want in f['files'].items():
        if sha(ROOT/relative)!=want:raise RuntimeError('Frozen source/input changed: '+relative)
    return sha(ROOT/'data/freeze.json')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def environment():
    return {'utc':now(),'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'cpu_count':os.cpu_count(),
      'affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
      'loadavg':os.getloadavg(),'gc_enabled':gc.isenabled(),'clocks':{k:vars(time.get_clock_info(k)) for k in ('perf_counter','process_time')},
      'timing_qualification':'shared cloud single process; no exclusive CPU pinning or cloud billing evidence'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out-dir',default='results/main');args=ap.parse_args()
    out=(ROOT/args.out_dir).resolve()
    if ROOT not in out.parents:raise SystemExit('Output must be inside experiment subtree')
    out.mkdir(parents=True,exist_ok=False)
    freeze_sha=check_freeze(); protocol=load(ROOT/'data/protocol.json');maps=load(ROOT/'data/maps.json');queries=load(ROOT/'data/queries.json');by_id={m['map_id']:m for m in maps}
    write(out/'environment_before.json',environment());write(out/'ledger.json',{'status':'started','started_utc':now(),'freeze_sha256':freeze_sha,'planned_measured_calls':protocol['planned_measured_calls'],'planned_replay_calls':protocol['planned_replay_calls'],'warmups':2})
    oracle={}; geometry={}
    for m in maps:
        free=geometry_free(m);geometry[m['map_id']]={'free_cells':len(free),'total_cells':m['width']*m['height']}
        for q in (x for x in queries if x['map_id']==m['map_id']):
            exact=bfs_oracle(m,q,free);oracle[q['query_id']]=exact
            if exact!=q['oracle_steps'] or (exact is not None)!=q['expected_reachable']:raise RuntimeError('Oracle mismatch')
    write(out/'independent_oracles.json',{'queries':oracle,'maps':geometry})
    warmups=[]
    for alg in protocol['algorithms']:
        q=queries[0];res=plan(by_id[q['map_id']],q,alg);warmups.append({'algorithm':alg,'query_id':q['query_id'],'output':res,'validation':validate(by_id[q['map_id']],q,res,oracle[q['query_id']])})
    write(out/'warmups.json',warmups)
    if not all(x['validation']['valid'] for x in warmups):raise RuntimeError('Warmup failed')
    records=[];call=0;batch_wall=time.perf_counter();batch_cpu=time.process_time()
    with (out/'raw.jsonl').open('x') as fh:
        for repeat in range(protocol['timing_repeats']):
            for qi,q in enumerate(queries):
                order=protocol['algorithms'] if (qi+repeat)%2==0 else protocol['algorithms'][::-1]
                for position,alg in enumerate(order):
                    call+=1;m=by_id[q['map_id']];c0=time.process_time_ns();w0=time.perf_counter_ns();error=None
                    try:res=plan(m,q,alg)
                    except Exception as exc:res=None;error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
                    w1=time.perf_counter_ns();c1=time.process_time_ns()
                    validation=validate(m,q,res,oracle[q['query_id']]) if error is None else {'valid':False,'errors':['execution_error']}
                    record={'run_id':f'main_{call:04d}','role':'measured','map_id':q['map_id'],'query_id':q['query_id'],'algorithm':alg,'repeat':repeat+1,'within_pair_position':position+1,
                         'cpu_ns':c1-c0,'wall_ns':w1-w0,'output':res,'error':error,'validation':validation}
                    fh.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n');fh.flush();records.append(record)
            print(f'measured repeat {repeat+1}: {len(records)} calls',flush=True)
    main_wall=time.perf_counter()-batch_wall;main_cpu=time.process_time()-batch_cpu
    reference={(r['query_id'],r['algorithm']):r for r in records if r['repeat']==1}
    replay_count=0;replay_fail=0
    with (out/'replay.jsonl').open('x') as fh:
        for q in queries:
            for alg in protocol['algorithms']:
                m=by_id[q['map_id']];res=plan(m,q,alg);v=validate(m,q,res,oracle[q['query_id']]);original=reference[q['query_id'],alg]['output'];same=res==original
                replay_count+=1;replay_fail+=not (v['valid'] and same)
                fh.write(json.dumps({'role':'deterministic_replay','query_id':q['query_id'],'algorithm':alg,'output':res,'validation':v,'exact_original_output_match':same},allow_nan=False)+'\n')
    check_freeze();write(out/'environment_after.json',environment())
    write(out/'ledger.json',{'status':'completed','completed_utc':now(),'freeze_sha256':freeze_sha,'measured_calls':len(records),'replay_calls':replay_count,'warmup_calls':2,
        'measured_validation_failures':sum(not r['validation']['valid'] for r in records),'execution_errors':sum(r['error'] is not None for r in records),'replay_failures':replay_fail,
        'main_loop_wall_s_including_validation_io':main_wall,'main_loop_cpu_s_including_validation_io':main_cpu,'notes':'Solver CPU/wall is per-call in raw.jsonl; loop totals also include independent acceptance and IO.'})
    print(json.dumps(load(out/'ledger.json'),indent=2))
if __name__=='__main__':main()
