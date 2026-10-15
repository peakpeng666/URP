#!/usr/bin/python3
"""Compare the same locked standard build, keeping each output and time log."""
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

base=Path(__file__).resolve().parent
root=base.parents[2]
destination=base/'build-performance.json'
if destination.exists(): raise FileExistsError(destination)
rows=[]
for repeat in range(3):
    for threads in ([0,8,4] if repeat%2==0 else [4,8,0]):
        env=os.environ.copy()
        if threads:env['RAYON_NUM_THREADS']=str(threads)
        out=base/'runtime'/f'build-{repeat}-{threads}'
        timing=base/'logs'/f'build-{repeat}-{threads}-time.json'
        log=base/'logs'/f'build-{repeat}-{threads}.log'
        started=time.perf_counter()
        with log.open('x') as stream:
            done=subprocess.run(['/usr/bin/time','-f','{"wall_s":%e,"user_s":%U,"system_s":%S,"max_rss_kib":%M}',
                '-o',str(timing),'npm','run','build','--','--outDir',str(out),'--emptyOutDir','false'],
                cwd=root/'src/frontend',env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
        if done.returncode:raise RuntimeError(str(log))
        assets={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
        rows.append({'repeat':repeat,'rayon_threads':threads,'elapsed_s':time.perf_counter()-started,
                     'timing':json.loads(timing.read_text()),'files':assets})
        destination.write_text(json.dumps({'status':'running','rows':rows},indent=2)+'\n')
        print(repeat,threads,round(rows[-1]['elapsed_s'],4),flush=True)
summary=[{'rayon_threads':threads,'median_s':statistics.median(r['elapsed_s'] for r in rows if r['rayon_threads']==threads)} for threads in [0,8,4]]
destination.write_text(json.dumps({'status':'complete','outputs_identical':all(r['files']==rows[0]['files'] for r in rows),
    'summary':summary,'rows':rows},indent=2)+'\n')
