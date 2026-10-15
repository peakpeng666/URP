#!/usr/bin/env python3
"""Small, repeatable hardware checks; never loads formal cases or invokes models."""
import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path.insert(0, str(ROOT / 'src/research/src'))


def solver_task(_):
    from urp_research.turn_modes.generate_data import grid
    from urp_research.turn_modes import solver, checker
    instance = grid(3,3,5,8000,'uturn')
    for _ in range(16):
        solution,_ = solver.solve(instance,'mode')
    assert checker.check(instance,solution)['valid']
    stable={k:v for k,v in solution.items() if k not in ('cpu_s','wall_s','preprocess_wall_s')}
    return hashlib.sha256(json.dumps(stable,sort_keys=True).encode()).hexdigest()


def child(mode, workers):
    start=time.perf_counter()
    if mode=='solver':
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
            values=list(pool.map(solver_task,range(128),chunksize=4))
        digest=hashlib.sha256(''.join(values).encode()).hexdigest()
        details={'unique_outputs':len(set(values)),'tasks':128,'repetitions_per_task':16,'workers':workers}
    else:
        import numpy as np
        rng=np.random.default_rng(8000)
        a=rng.normal(size=(768,768));b=rng.normal(size=(768,768))
        warmup=a@b
        begin=time.perf_counter()
        for _ in range(16): c=a@b
        assert np.allclose(warmup,c,rtol=1e-12,atol=1e-12)
        # Tolerant checksum is separate from timing; BLAS reduction order can differ.
        digest=hashlib.sha256(np.round(c,8).tobytes()).hexdigest()
        details={'matrix_shape':[768,768],'matmuls':16,'kernel_seconds':time.perf_counter()-begin,
                 'checksum_sum':float(c.sum()),'max_abs':float(np.abs(c).max()),'numpy':np.__version__}
    own=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
    print(json.dumps({'mode':mode,'wall_seconds':time.perf_counter()-start,'digest':digest,**details,
                     'cpu_seconds':own.ru_utime+own.ru_stime+children.ru_utime+children.ru_stime,
                     'peak_single_process_rss_kib':max(own.ru_maxrss,children.ru_maxrss)}))


def suite():
    destination=BASE/'performance.json'
    if destination.exists(): raise FileExistsError(destination)
    rows=[]
    # Interleaved repeats reduce order bias; warm caches are explicitly part of this check.
    solver_python=ROOT/'src/research/.venv/bin/python'
    numpy_python=ROOT/'src/frontend/.venv/bin/python'
    configurations=[('solver',n) for n in (1,4,8,12,24)]+[('blas',n) for n in (0,1,4,8,12)]
    for repeat in range(3):
        order=configurations if repeat%2==0 else configurations[::-1]
        for mode,n in order:
            env=os.environ.copy()
            if mode=='solver' or n:
                for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
                    env[key]=str(1 if mode=='solver' else n)
            command=[str(solver_python if mode=='solver' else numpy_python),str(Path(__file__).resolve()),mode,'--workers',str(n or 1)]
            reply=subprocess.run(command,env=env,text=True,capture_output=True,timeout=60)
            if reply.returncode: raise RuntimeError(reply.stderr)
            row=json.loads(reply.stdout);row.update(repeat=repeat,configuration=n)
            rows.append(row);destination.write_text(json.dumps({'status':'running','rows':rows},indent=2)+'\n')
            print(mode,n,round(row['wall_seconds'],4),flush=True)
    summary=[]
    for mode,n in configurations:
        samples=[r for r in rows if r['mode']==mode and r['configuration']==n]
        summary.append({'mode':mode,'configuration':n,'median_seconds':statistics.median(r['wall_seconds'] for r in samples),
                        'samples_seconds':[r['wall_seconds'] for r in samples],
                        'max_rss_kib':max(r['peak_single_process_rss_kib'] for r in samples),
                        'digests':sorted({r['digest'] for r in samples})})
    destination.write_text(json.dumps({'status':'complete','scope':'Single 3x3 synthetic routing fixture repeated; synthetic NumPy matrix multiply',
                                      'new_model_calls':0,'formal_cases_loaded':0,'rows':rows,'summary':summary},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('solver','blas','suite'))
    parser.add_argument('--workers',type=int,default=1)
    args=parser.parse_args()
    if args.mode=='suite':suite()
    else:child(args.mode,args.workers)
