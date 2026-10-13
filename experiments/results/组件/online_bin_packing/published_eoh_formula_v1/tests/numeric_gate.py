"""Prospective bounded numerical tests; this file has not been executed.

Run only after the exact preparation and numerical gate receive separate approval.
No downloaded author module/bytes or second purportedly independent formula runs.
"""
import hashlib,json,os,pathlib,resource,sys,traceback
SRC=pathlib.Path(__file__).resolve().parents[1]/'src';sys.path.insert(0,str(SRC))
from warning_capture import WarningJournal
AS=2147483648

def require_limits():
    expected={'RLIMIT_AS':(AS,AS),'RLIMIT_CPU':(20,20),'RLIMIT_FSIZE':(0,0),'RLIMIT_NOFILE':(32,32)}
    actual={k:resource.getrlimit(getattr(resource,k)) for k in expected}
    if actual!=expected:raise RuntimeError('missing exact reviewed worker limits')
    return actual

def gate(journal):
    import numpy as np
    from formula import score_trace
    if np.__version__!='2.3.5':raise RuntimeError('NumPy version mismatch')
    with (SRC.parent/'static_preparation_freeze.json').open('rb') as f:manifest_raw=f.read(1000001)
    if len(manifest_raw)>1000000:raise RuntimeError('manifest bound')
    frozen=json.loads(manifest_raw)
    if str(pathlib.Path(np.__file__).resolve().parent)!=frozen['environment']['numpy_package_root']:raise RuntimeError('actual NumPy package root mismatch')
    def invoke(item,bins):
        before=bins.tobytes();shape=bins.shape;dtype=bins.dtype
        try:return score_trace(item,bins)
        finally:
            if bins.tobytes()!=before or bins.shape!=shape or bins.dtype!=dtype:raise AssertionError('input bins mutated')
    summaries=[];pair_count=0;overflow_pairs=0
    journal.phase='gate'
    with np.errstate(divide='warn',over='warn',invalid='warn',under='ignore'):
        for raw_item in range(1,101):
            item=np.int32(raw_item);bins=np.arange(raw_item,501,dtype=np.int64)
            journal.item_index=raw_item
            tr=invoke(item,bins);d=tr['diff'];expected_inf=d>=355
            if tr['diff'].dtype!=np.dtype('int64'):raise AssertionError('diff dtype')
            for key,value in tr.items():
                if key!='diff' and value.dtype!=np.dtype('float64'):raise AssertionError('floating dtype '+key)
                if np.any(np.isnan(value)) or np.any(np.isneginf(value)):raise AssertionError('unexpected nonfinite '+key)
                if key!='denominator' and not np.all(np.isfinite(value)):raise AssertionError('unexpected infinity '+key)
            if not np.array_equal(np.isposinf(tr['denominator']),expected_inf):raise AssertionError('overflow boundary')
            zeros=tr['hybrid_exp'][expected_inf]
            if np.any(zeros!=0) or np.any(np.signbit(zeros)):raise AssertionError('expected positive zero')
            # Exact-fit boundary, source-derived identity (no alternate general formula).
            if d[0]!=0 or tr['exp'][0]!=1 or tr['sqrt'][0]!=0 or tr['ulti'][0]!=1 or tr['comb'][0]!=0 or tr['adjust'][0]!=np.float64(.3):raise AssertionError('exact-fit boundary')
            # Verify only source-derived branch selection, not independent numerical proof.
            for dd in [3*raw_item-1,3*raw_item,3*raw_item+1,354,355]:
                if 0<=dd<len(bins):
                    increment=np.float64(.8 if dd>3*raw_item else .3)
                    if tr['adjust'][dd]!=tr['comb'][dd]+increment:raise AssertionError('strict branch boundary')
            summaries.append({'item':raw_item,'pairs':len(bins),'intermediate_sha256':{k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in tr.items()},'score_dtype':str(tr['scores'].dtype)})
            pair_count+=len(bins);overflow_pairs+=int(np.count_nonzero(expected_inf))
        # Every exhaustive call has an overflowing denominator; capture must not be empty.
        domain_warning_events=[e for e in journal.events if e[0]=='gate' and type(e[1]) is int and 1<=e[1]<=100]
        if len(domain_warning_events)!=100 or {e[1] for e in domain_warning_events}!=set(range(1,101)):raise AssertionError('expected overflow warnings missing/duplicated')
        journal.item_index='no_exact_fit_override'
        example=invoke(np.int32(1),np.array([1,5],dtype=np.int64))
        if int(np.argmax(example['scores']))!=1:raise AssertionError('forced exact-fit override')
        # Same implementation across actual contiguous feasible layouts, no tolerance.
        layouts=[]
        for length in [1,2,17,1000,10000]:
            bins=np.resize(np.array([1,2,4,5,355,356,499,500],dtype=np.int64),length)
            for label,b in [('forward',bins),('reverse',bins[::-1].copy()),('equal',np.full(length,500,dtype=np.int64))]:
                journal.item_index=f'{length}_{label}'
                tr=invoke(np.int32(1),b)
                unique=np.unique(b);base=invoke(np.int32(1),unique)
                indices=np.searchsorted(unique,b)
                for key in tr:
                    if not np.array_equal(tr[key].view(np.uint64),base[key][indices].view(np.uint64)):raise AssertionError('layout bitwise drift '+key)
                scores=tr['scores'];picked=int(np.argmax(scores));ties=np.flatnonzero(scores==np.max(scores))
                if picked!=int(ties[0]):raise AssertionError('stable first maximum')
                layouts.append({'length':length,'layout':label,'score_sha256':hashlib.sha256(scores.tobytes()).hexdigest(),'first_argmax':picked,'tie_count':len(ties)})
        rejects=0
        for item,b in [(True,np.array([1],dtype=np.int64)),(1,np.array([1],dtype=np.int64)),(np.int32(0),np.array([1],dtype=np.int64)),(np.int32(101),np.array([101],dtype=np.int64)),(np.int32(1),np.array([],dtype=np.int64)),(np.int32(1),np.array([[1]],dtype=np.int64)),(np.int32(1),np.array([1],dtype=np.int32)),(np.int32(2),np.array([1],dtype=np.int64)),(np.int32(1),np.array([501],dtype=np.int64)),(np.int32(1),np.ones(10001,dtype=np.int64))]:
            try:invoke(item,b)
            except ValueError:rejects+=1
            else:raise AssertionError('domain rejection missing')
    expected_line=next(i for i,line in enumerate((SRC/'formula.py').read_text().splitlines(),1) if line.strip()=='denominator = (exp + 0.7) * exp')
    for k in journal.kinds:
        if (k['category'],k['filename'],k['line'],k['message'])!=('RuntimeWarning','formula.py',expected_line,'overflow encountered in multiply'):raise AssertionError('unexpected warning '+str(k))
    if pair_count!=45050:raise AssertionError('domain count')
    if overflow_pairs!=9550:raise AssertionError('analytical overflow pair count')
    return {'status':'passed','pair_count':pair_count,'denominator_infinite_pairs':overflow_pairs,'expected_domain_warning_events':100,'input_mutation_checks':'byte-identical values/shape/dtype on every call','no_exact_fit_override_example':'item1,bins1and5 selects index1','domain_rejections':rejects,'item_summaries':summaries,'layouts':layouts,'numpy_version':np.__version__,'dtype_contract':{'item':'int32','bins':'int64','diff':'int64','floating':'float64'},'reference_claim':'Source mapping and analytic boundary/property checks only; no empirical author-byte execution parity'}

def main():
    limits=require_limits();journal=WarningJournal();result=None;error=None
    try:
        with journal:result=gate(journal)
    except Exception as exc:
        error={'type':type(exc).__name__,'message':str(exc)[:2000]};traceback.print_exc(file=sys.stderr)
    out={'result':result,'error':error,'warnings':journal.payload(),'limits':limits,'pid':os.getpid()}
    encoded=json.dumps(out,separators=(',',':'),allow_nan=False).encode()
    if len(encoded)>400000:raise RuntimeError('bounded stdout exceeded')
    sys.stdout.buffer.write(encoded);sys.stdout.buffer.flush()
    if error is not None:raise SystemExit(1)
if __name__=='__main__':main()
