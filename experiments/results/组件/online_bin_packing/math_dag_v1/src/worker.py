"""One bounded trusted interpreter request; candidate material is JSON data only."""
import hashlib,json,os,pathlib,resource,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from schema import validate_program,strict_json,StructureError
from warnings_log import WarningLog,DiagnosticLimit,UnexpectedWarning
AS=2147483648
class RequestInvalid(ValueError):pass

def effective_limits():return {k:list(resource.getrlimit(getattr(resource,k))) for k in ['RLIMIT_AS','RLIMIT_CPU','RLIMIT_FSIZE','RLIMIT_NOFILE']}
def main():
 limits=effective_limits()
 if limits!={'RLIMIT_AS':[AS,AS],'RLIMIT_CPU':[20,20],'RLIMIT_FSIZE':[0,0],'RLIMIT_NOFILE':[32,32]}:raise RuntimeError('required limits missing')
 status='infrastructure_failure';error=None;result=None;log=WarningLog();work=None;program=None;phase='request';exitcode=0
 expected_errors={StructureError:'structural_rejected',RequestInvalid:'input_rejected',DiagnosticLimit:'diagnostic_unresolved',MemoryError:'resource_unresolved'}
 try:
  raw=sys.stdin.buffer.read(100001)
  if len(raw)>100000:raise RequestInvalid('request byte bound')
  try:d=strict_json(raw)
  except StructureError as exc:raise RequestInvalid('request JSON: '+str(exc)) from exc
  if type(d) is not dict or type(d.get('mode')) is not str or d['mode'] not in {'validate','evaluate','pack'}:raise RequestInvalid('request mode')
  keys={'validate':{'mode','program_json'},'evaluate':{'mode','program_json','item','bins'},'pack':{'mode','program_json','items','capacity'}}[d['mode']]
  if set(d)!=keys or type(d.get('program_json')) is not str:raise RequestInvalid('request fields')
  phase='structure'
  try:program_raw=d['program_json'].encode('utf-8')
  except UnicodeError as exc:raise StructureError('program Unicode') from exc
  program=validate_program(program_raw)
  if d['mode']=='validate':
   status='validated_structure';result={'nodes':len(program.nodes),'types':list(program.types),'return_node':program.return_node}
  else:
   phase='runtime_initialization'
   with log:
    import numpy as np
    from interpreter import evaluate,pack,WorkBudget,InputInvalid,NumericInvalid,WorkLimit,ContractFault
    expected_errors.update({InputInvalid:'input_rejected',NumericInvalid:'numeric_invalid',WorkLimit:'resource_unresolved'})
    if np.__version__!='2.3.5':raise RuntimeError('NumPy version')
    expected_root=pathlib.Path(sys.prefix)/('lib/python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'/site-packages/numpy')
    if pathlib.Path(np.__file__).resolve().parent!=expected_root.resolve():raise RuntimeError('NumPy package root')
    work=WorkBudget();phase=d['mode']
    if d['mode']=='evaluate':
     item=d['item'];bins=d['bins']
     if type(item) is not int or not 1<=item<=100 or type(bins) is not list or not 1<=len(bins)<=10000 or any(type(v) is not int or not item<=v<=500 for v in bins):raise InputInvalid('raw numeric input')
     values=np.array(bins,dtype=np.int64);before=values.tobytes()
     evaluated=evaluate(program,np.int32(item),values,work,log,trace=True)
     if values.tobytes()!=before:raise ContractFault('input mutation')
     scores=evaluated['scores'];result={'dtype':str(scores.dtype),'shape':list(scores.shape),'scores_sha256':hashlib.sha256(scores.tobytes()).hexdigest(),'scores':scores.tolist() if len(scores)<=16 else None,'first_argmax':int(np.argmax(scores)),'node_trace':evaluated['trace']}
     status='completed_finite'
    else:
     result=pack(program,d['items'],d['capacity'],work,log);status='packing_returned'
 except Exception as exc:
  status=expected_errors.get(type(exc),'infrastructure_failure')
  error={'type':type(exc).__name__,'message':str(exc)[:2000]}
  if status=='infrastructure_failure':traceback.print_exc(file=sys.stderr);exitcode=1
 out={'status':status,'phase':phase,'error':error,'result':result,'program_sha256':None if program is None else program.raw_sha256,'canonical_program_sha256':None if program is None else program.canonical_sha256,'work_units':None if work is None else work.used,'numeric_intermediates':None if work is None else work.numeric_counts,'warnings':log.payload(),'pid':os.getpid(),'limits':limits}
 raw=json.dumps(out,separators=(',',':'),allow_nan=False).encode()
 if len(raw)>400000:raise RuntimeError('stdout byte bound')
 sys.stdout.buffer.write(raw);sys.stdout.buffer.flush()
 if exitcode:raise SystemExit(exitcode)
if __name__=='__main__':main()
