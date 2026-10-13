"""Fixed NumPy interpretation of validated mathematical DAG data, not Python code."""
import hashlib
import numpy as np
from schema import Program,INTEGER_BOUND

class NumericInvalid(ValueError):pass
class InputInvalid(ValueError):pass
class WorkLimit(RuntimeError):pass
class ContractFault(RuntimeError):pass

class WorkBudget:
 def __init__(self,limit=5000000):
  if type(limit) is not int or not 0<=limit<=5000000:raise ValueError('work budget')
  self.limit=limit;self.used=0
  self.numeric_counts={'completed_nodes':0,'nan_elements':0,'positive_infinity_elements':0,'negative_infinity_elements':0}
 def charge(self,amount):
  if type(amount) is not int or amount<0:raise ContractFault('bad work charge')
  if self.used+amount>self.limit:raise WorkLimit('work budget exhausted')
  self.used+=amount

def check_value(value,tag,n):
 if tag=='i32':ok=type(value) is np.int32
 elif tag=='f64':ok=type(value) is np.float64
 else:
  dtype={'vi64':np.dtype('int64'),'vf64':np.dtype('float64'),'vb':np.dtype('bool')}[tag]
  ok=type(value) is np.ndarray and value.dtype==dtype and value.shape==(n,)
 if not ok:raise ContractFault('unexpected dtype/shape for '+tag)
 if tag in {'i32','vi64'} and np.any(np.abs(value)>INTEGER_BOUND):raise ContractFault('integer invariant')

def checked_integer(op,a,b,tag):
 # Every integer input is <=1e6 in magnitude. Widened products <=1e12,
 # so the check itself cannot overflow int64. Never silently wrap int32.
 aa=np.int64(a) if type(a) is np.int32 else a
 bb=np.int64(b) if type(b) is np.int32 else b
 if op=='add':v=np.add(aa,bb)
 elif op=='sub':v=np.subtract(aa,bb)
 elif op=='mul':v=np.multiply(aa,bb)
 else:raise ContractFault('integer operation')
 if np.any(np.abs(v)>INTEGER_BOUND):raise NumericInvalid('integer bound/overflow rejected')
 return np.int32(v) if tag=='i32' else v

def trace_value(value,tag):
 a=np.asarray(value)
 return {'type':tag,'dtype':str(a.dtype),'shape':list(a.shape),'sha256':hashlib.sha256(a.tobytes()).hexdigest(),
  'nan_count':int(np.count_nonzero(np.isnan(a))) if tag!='vb' else 0,
  'positive_infinity_count':int(np.count_nonzero(np.isposinf(a))) if tag!='vb' else 0,
  'negative_infinity_count':int(np.count_nonzero(np.isneginf(a))) if tag!='vb' else 0}

def evaluate(program,item,bins,work,warnings=None,placement=0,trace=False):
 if type(program) is not Program:raise ContractFault('validated program required')
 if type(item) is not np.int32 or not 1<=int(item)<=100:raise InputInvalid('item domain/type')
 if type(bins) is not np.ndarray or bins.dtype!=np.dtype('int64') or bins.ndim!=1 or not 1<=len(bins)<=10000 or np.any(bins<item) or np.any(bins>500):raise InputInvalid('feasible bins domain/type/length')
 n=len(bins);constants=[np.int32(v) if t=='i32' else np.float64(v) for t,v in program.constants];values=[];traces=[]
 def resolve(arg):
  if type(arg) is int:return values[arg]
  if arg=='item':return item
  if arg=='bins':return bins
  return constants[int(arg[1:])]
 with np.errstate(divide='warn',over='warn',invalid='warn',under='ignore'):
  for i,(node,tag) in enumerate(zip(program.nodes,program.types)):
   work.charge(n) # All nodes, including scalar/dead nodes, conservatively charged n.
   if warnings is not None:warnings.current_placement=placement;warnings.current_node=i
   op=node[0];args=[resolve(x) for x in node[1:]]
   if op in {'add','sub','mul'} and tag in {'i32','vi64'}:value=checked_integer(op,*args,tag)
   elif op=='add':value=np.add(*args)
   elif op=='sub':value=np.subtract(*args)
   elif op=='mul':value=np.multiply(*args)
   elif op=='div':value=np.divide(*args)
   elif op=='exp':value=np.exp(*args)
   elif op=='sqrt':value=np.sqrt(*args)
   elif op=='gt':value=np.greater(*args)
   elif op=='where':value=np.where(*args)
   else:raise ContractFault('unreachable operation')
   check_value(value,tag,n)
   work.numeric_counts['completed_nodes']+=1
   if tag in {'f64','vf64'}:
    work.numeric_counts['nan_elements']+=int(np.count_nonzero(np.isnan(value)))
    work.numeric_counts['positive_infinity_elements']+=int(np.count_nonzero(np.isposinf(value)))
    work.numeric_counts['negative_infinity_elements']+=int(np.count_nonzero(np.isneginf(value)))
   values.append(value)
   if trace:traces.append(trace_value(value,tag))
 scores=values[program.return_node]
 if not np.all(np.isfinite(scores)):raise NumericInvalid('nonfinite final score')
 return {'scores':scores,'trace':traces,'values':values if trace else None,'work_units':work.used}

def pack(program,items,capacity,work,warnings=None):
 if type(items) is not list or len(items)>256 or type(capacity) is not int or not 1<=capacity<=500 or any(type(v) is not int or not 1<=v<=min(capacity,100) for v in items):raise InputInvalid('packing domain/placement count')
 n=len(items);bins=np.full(n,capacity,dtype=np.int64);assignment=[];counts=[]
 for i,item in enumerate(items):
  work.charge(n) # Fixed all-bin feasibility scan is charged separately.
  indices=np.flatnonzero(bins-item>=0)
  if not len(indices):raise ContractFault('no feasible preallocated bin')
  result=evaluate(program,np.int32(item),bins[indices],work,warnings,i)
  chosen=int(indices[int(np.argmax(result['scores']))]);bins[chosen]-=item
  assignment.append(chosen);counts.append(int(len(indices)))
 return {'assignment':assignment,'residuals':bins.tolist(),'used_bins':int(np.count_nonzero(bins!=capacity)),'feasible_counts':counts,'work_units':work.used,'placements':n}
