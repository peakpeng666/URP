#!/usr/bin/env python3
"""Public entry for the current CVRP library; frozen solver bytes remain unchanged."""
import argparse,datetime,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'protocol/formal_plan.json';CASES=ROOT/'src/research/configs/cvrplib_cases.json'

def algorithms():return json.loads(PLAN.read_text())['algorithms']
def cases():return json.loads(CASES.read_text())['cases']
def output_path(name):
    root=(ROOT/'user-runs').resolve();out=(root/name).resolve()
    if out==root or root not in out.parents:raise ValueError('输出必须为user-runs下面的新目录，不覆盖正式证据')
    return out

def solve(case_id,algorithm,seed=0,budget=5,run_name=None):
    """Run and independently score one canonical case. Returns result/evaluation paths.

    This executes optimization; ordinary imports and algorithms()/cases() do not.
    It uses the existing acceptance CLI and a separate user-run registry.
    """
    if algorithm not in algorithms():raise ValueError('Unknown current algorithm')
    case=next((c for c in cases() if c['case_id']==case_id),None)
    if not case:raise ValueError('Unknown canonical case')
    name=run_name or datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=output_path(name)
    if out.exists():raise FileExistsError(str(out))
    out.parent.mkdir(parents=True,exist_ok=True)
    cmd=[sys.executable,str(ROOT/'src/research/scripts/cvrplib.py'),'run-one','--instance',str(ROOT/case['instance_path']),'--algorithm',algorithm,'--seed',str(seed),'--budget',str(budget),'--output',str(out),'--run-registry',str(out.parent/(out.name+'-registry'))]
    run=subprocess.run(cmd,cwd=ROOT)
    result=out/'result.json';evaluation=out/'evaluation.json'
    if result.exists():
        raw=json.loads(result.read_text())
        if 'case_manifest_sha256' in raw:
            subprocess.run([sys.executable,str(ROOT/'src/research/scripts/cvrplib.py'),'score','--repo',str(ROOT),'--result',str(result),'--output',str(evaluation)],cwd=ROOT)
    return {'returncode':run.returncode,'result':str(result),'evaluation':str(evaluation) if evaluation.exists() else None,'purpose':'separate_user_run_not_original_baseline'}

def main():
    p=argparse.ArgumentParser(description='当前17配置CVRP算法库：列举、单例、复现、汇总、验算。')
    sp=p.add_subparsers(dest='command',required=True)
    sp.add_parser('algorithms',help='列出本轮17个算法配置ID')
    sp.add_parser('cases',help='列出53问题、规模及底本ID')
    one=sp.add_parser('run',help='在user-runs新目录运行并独立评分一个问题');one.add_argument('--case',required=True);one.add_argument('--algorithm',choices=algorithms(),required=True);one.add_argument('--seed',type=int,default=0);one.add_argument('--budget',type=int,choices=[1,5],default=5);one.add_argument('--name')
    rep=sp.add_parser('reproduce',help='显示完整4505项复现命令；--execute才执行');rep.add_argument('--name',required=True);rep.add_argument('--execute',action='store_true')
    verify=sp.add_parser('verify',help='独立重新验算一个已有result.json');verify.add_argument('--result',required=True,type=Path);verify.add_argument('--name',required=True)
    summary=sp.add_parser('summarize',help='按主机/资源批次汇总正式计划');summary.add_argument('--runs',required=True,type=Path,nargs='+');summary.add_argument('--out',required=True,type=Path);summary.add_argument('--assignment',type=Path,default=ROOT/'protocol/ownership_assignment_v3.json')
    a=p.parse_args()
    if a.command=='algorithms':print('\n'.join(algorithms()));return
    if a.command=='cases':
        print('case_id\tcustomers\tsize\tfamily\tbase_id')
        for c in cases():print('\t'.join(str(c[k]) for k in ('case_id','n_customers','size_stratum','source_family','base_id')))
        return
    if a.command=='run':print(json.dumps(solve(a.case,a.algorithm,a.seed,a.budget,a.name),ensure_ascii=False));return
    if a.command=='reproduce':
        out=output_path(a.name)
        if out.exists():raise FileExistsError(str(out))
        cmd=[sys.executable,str(ROOT/'scripts/run_formal.py'),'--plan',str(PLAN),'--output',str(out)]
        print(json.dumps({'planned':4505,'new_independent_replication':True,'command':cmd},ensure_ascii=False))
        if a.execute:subprocess.run(cmd,cwd=ROOT,check=True)
        return
    if a.command=='verify':
        out=output_path(a.name);out.mkdir(parents=True,exist_ok=False)
        subprocess.run([sys.executable,str(ROOT/'src/research/scripts/cvrplib.py'),'score','--repo',str(ROOT),'--result',str(a.result.resolve()),'--output',str(out/'evaluation.json')],cwd=ROOT,check=True);return
    if a.command=='summarize':
        subprocess.run([sys.executable,str(ROOT/'protocol/aggregate_hosts.py'),'--plan',str(PLAN),'--cases',str(CASES),'--distribution',str(ROOT/'protocol/distribution_metadata.json'),'--runs',*[str(x.resolve()) for x in a.runs],'--assignment',str(a.assignment.resolve()),'--out',str(a.out.resolve())],cwd=ROOT,check=True)
if __name__=='__main__':main()
