"""Fixed trusted formula reimplementation only; no source/module input accepted."""
import json,os,pathlib,resource,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parent))
from published_eoh_formula_v1.src.warning_capture import WarningJournal
AS=2147483648

def limits():return {k:list(resource.getrlimit(getattr(resource,k))) for k in ['RLIMIT_AS','RLIMIT_CPU','RLIMIT_FSIZE','RLIMIT_NOFILE']}
def require_limits():
    if limits()!={'RLIMIT_AS':[AS,AS],'RLIMIT_CPU':[20,20],'RLIMIT_FSIZE':[0,0],'RLIMIT_NOFILE':[32,32]}:raise RuntimeError('effective worker limits mismatch')
def pack(items,capacity,journal):
    import numpy as np
    from published_eoh_formula_v1.src.formula import score
    if np.__version__!='2.3.5':raise RuntimeError('NumPy version mismatch')
    protocol=json.loads((ROOT/'protocol.json').read_text())
    if str(pathlib.Path(np.__file__).resolve().parent)!=protocol['runtime']['numpy_package_root']:raise RuntimeError('actual NumPy root mismatch')
    if type(capacity) is not int or not 1<=capacity<=500 or type(items) is not list or len(items)>10000 or any(type(x) is not int or not 1<=x<=min(capacity,100) for x in items):raise ValueError('input domain')
    source_items=np.array(items,dtype=np.int32);residuals=np.full(len(items),capacity,dtype=np.int64)
    assignment=[];counts=[];journal.phase='pack'
    with np.errstate(divide='warn',over='warn',invalid='warn',under='ignore'):
        for i,item in enumerate(source_items):
            journal.item_index=i
            indices=np.flatnonzero(residuals-item>=0)
            if indices.size==0:raise ValueError('no feasible bin')
            candidates=residuals[indices];before=candidates.tobytes()
            scores=score(item,candidates)
            if candidates.tobytes()!=before:raise RuntimeError('formula mutated feasible input')
            if scores.shape!=candidates.shape or not np.all(np.isfinite(scores)):raise RuntimeError('invalid score vector')
            chosen=int(indices[int(np.argmax(scores))]);residuals[chosen]-=item
            assignment.append(chosen);counts.append(int(indices.size))
    line=next(i for i,s in enumerate((ROOT.parent/'published_eoh_formula_v1/src/formula.py').read_text().splitlines(),1) if s.strip()=='denominator = (exp + 0.7) * exp')
    for k in journal.kinds:
        if (k['category'],k['filename'],k['line'],k['message'])!=('RuntimeWarning','formula.py',line,'overflow encountered in multiply'):raise RuntimeError('unexpected warning')
    expected_warning_indices=[i for i,item in enumerate(items) if capacity-item>=355]
    if [e[1] for e in journal.events]!=expected_warning_indices or any(e[0]!='pack' for e in journal.events):raise RuntimeError('missing/extra/reordered expected overflow warnings')
    return {'assignment':assignment,'residuals':residuals.tolist(),'used_bins':int(np.count_nonzero(residuals!=capacity)),'feasible_counts':counts,'n_bin_feasibility_checks':len(items)**2,'numpy_version':np.__version__,'method':'EOH_formula_reimplementation'}
def main():
    require_limits();journal=WarningJournal();start=time.monotonic();cpu=time.process_time();result=None;error=None
    try:
        raw=sys.stdin.buffer.read(100001)
        if len(raw)>100000:raise ValueError('input byte bound')
        d=json.loads(raw)
        if set(d)!={'items','capacity','method'} or d['method']!='EOH_formula_reimplementation':raise ValueError('fixed method request')
        with journal:result=pack(d['items'],d['capacity'],journal)
    except Exception as exc:error={'type':type(exc).__name__,'message':str(exc)[:2000]};traceback.print_exc(file=sys.stderr)
    out=result or {};out.update({'error':error,'warnings':journal.payload(),'pid':os.getpid(),'effective_limits':limits(),'request_cpu_seconds_including_import':time.process_time()-cpu,'request_wall_seconds_including_import':time.monotonic()-start,'timer_scope':'Afterlimitselfcheck throughstdin/NumPyimport/packing;beforeoutputencoding. Use fullworkerCPU for cross-method cost,not this requesttimer.'})
    raw=json.dumps(out,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>400000:raise RuntimeError('stdout bound')
    sys.stdout.buffer.write(raw);sys.stdout.buffer.flush()
    if error is not None:raise SystemExit(1)
if __name__=='__main__':main()
