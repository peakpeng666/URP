from __future__ import annotations
import argparse,collections,json,pathlib
from run import check_freeze,load,write,sha
from validator import geometry_free,bfs_oracle,validate
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out-dir',default='results/main');args=ap.parse_args();out=(ROOT/args.out_dir).resolve()
    if ROOT not in out.parents:raise SystemExit('Output must stay in subtree')
    freeze_sha=check_freeze();maps={m['map_id']:m for m in load(ROOT/'data/maps.json')};queries={q['query_id']:q for q in load(ROOT/'data/queries.json')};oracles={}
    for mid,m in maps.items():
        free=geometry_free(m)
        for q in queries.values():
            if q['map_id']==mid:oracles[q['query_id']]=bfs_oracle(m,q,free)
    failures=[];counts=collections.Counter();outputs={};main_count=0
    for line in (out/'raw.jsonl').read_text().splitlines():
        r=json.loads(line);q=queries[r['query_id']];m=maps[q['map_id']];v=validate(m,q,r['output'],oracles[q['query_id']]);main_count+=1;counts[q['query_id'],r['algorithm']]+=1
        if not v['valid'] or v!=r['validation']:failures.append({'run_id':r['run_id'],'problem':'independent acceptance or saved validation mismatch','details':v})
        if r['cpu_ns']<=0 or r['wall_ns']<=0:failures.append({'run_id':r['run_id'],'problem':'nonpositive measured clock'})
        if r['repeat']==1:outputs[r['query_id'],r['algorithm']]=r['output']
    for qid in queries:
        for alg in ('astar','dijkstra'):
            if counts[qid,alg]!=5:failures.append({'problem':'count','query_id':qid,'algorithm':alg,'count':counts[qid,alg]})
        if outputs[qid,'astar']['cost_steps']!=outputs[qid,'dijkstra']['cost_steps']:failures.append({'problem':'paired cost mismatch','query_id':qid})
    replay_count=0
    for line in (out/'replay.jsonl').read_text().splitlines():
        r=json.loads(line);q=queries[r['query_id']];v=validate(maps[q['map_id']],q,r['output'],oracles[q['query_id']]);replay_count+=1
        if not v['valid'] or r['output']!=outputs[r['query_id'],r['algorithm']] or not r['exact_original_output_match']:failures.append({'problem':'replay','query_id':q['query_id'],'algorithm':r['algorithm']})
    if main_count!=960 or replay_count!=192:failures.append({'problem':'total count'})
    summary=load(out/'summary.json')
    for relative,want in summary['source_files'].items():
        if sha(ROOT/relative)!=want:failures.append({'problem':'source hash','path':relative})
    report={'passed':not failures,'frozen_files_verified':True,'freeze_sha256':freeze_sha,'main_calls_rechecked':main_count,'replay_calls_rechecked':replay_count,'independent_base_maps':len(maps),'paired_queries':len(queries),'failure_count':len(failures),'failures':failures}
    write(out/'verification.json',report);print(json.dumps(report,indent=2))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
