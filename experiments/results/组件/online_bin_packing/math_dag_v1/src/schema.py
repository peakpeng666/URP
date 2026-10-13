"""Closed JSON data validation/type inference. Never parses or executes Python."""
from dataclasses import dataclass
import hashlib,json,math,re
MAX_BYTES=32768;MAX_NODES=64;MAX_CONSTANTS=16;INTEGER_BOUND=1000000
NUMERIC={'i32','f64','vi64','vf64'}
ARITY={'add':2,'sub':2,'mul':2,'div':2,'exp':1,'sqrt':1,'gt':2,'where':3}

class StructureError(ValueError):pass
@dataclass(frozen=True)
class Program:
 description:str
 constants:tuple
 nodes:tuple
 types:tuple
 return_node:int
 raw_sha256:str
 canonical_sha256:str

def strict_json(raw):
 def finite(v):
  x=float(v)
  if not math.isfinite(x):raise StructureError('nonfinite JSON number')
  return x
 def reject(v):raise StructureError('nonstandard JSON constant')
 def pairs(ps):
  out={}
  for k,v in ps:
   if k in out:raise StructureError('duplicate JSON key')
   out[k]=v
  return out
 try:return json.loads(raw,parse_float=finite,parse_constant=reject,object_pairs_hook=pairs)
 except (ValueError,RecursionError,UnicodeError) as exc:raise StructureError(str(exc)[:1000]) from exc

def infer(op,types):
 if op=='where':
  if types[0]!='vb' or any(t not in {'f64','vf64'} for t in types[1:]):raise StructureError('where requires bool vector and float64 branches')
  return 'vf64'
 if any(t not in NUMERIC for t in types):raise StructureError('numeric operand required')
 vector=any(t.startswith('v') for t in types)
 if op=='gt':
  if not vector:raise StructureError('gt must have a vector operand')
  return 'vb'
 if op in {'div','exp','sqrt'}:return 'vf64' if vector else 'f64'
 floating=any(t in {'f64','vf64'} for t in types)
 return ('vf64' if floating else 'vi64') if vector else ('f64' if floating else 'i32')

def validate_program(raw):
 if type(raw) is not bytes or len(raw)>MAX_BYTES:raise StructureError('program byte limit/type')
 try:text=raw.decode('utf-8')
 except UnicodeError as exc:raise StructureError('UTF8 required') from exc
 d=strict_json(text)
 if type(d) is not dict or set(d)!={'schema','description','constants','nodes','return_node'} or d['schema']!='math-dag-v1':raise StructureError('top-level schema')
 description=d['description']
 if type(description) is not str or not description.strip() or any(ord(c)<32 or ord(c) in {127,133,8232,8233} for c in description):raise StructureError('one-line description without controls')
 try:description_bytes=description.encode('utf-8')
 except UnicodeError as exc:raise StructureError('description Unicode') from exc
 if len(description_bytes)>1024:raise StructureError('description byte bound')
 constants=d['constants']
 if type(constants) is not list or len(constants)>MAX_CONSTANTS:raise StructureError('constant count')
 cs=[]
 for c in constants:
  if type(c) is not dict or set(c)!={'type','value'} or type(c['type']) is not str or c['type'] not in {'i32','f64'}:raise StructureError('constant schema')
  v=c['value']
  if type(v) not in (int,float) or (c['type']=='i32' and type(v) is not int) or abs(v)>1000 or (type(v) is float and not math.isfinite(v)):raise StructureError('constant value/type/range')
  cs.append((c['type'],v))
 nodes=d['nodes']
 if type(nodes) is not list or not 1<=len(nodes)<=MAX_NODES:raise StructureError('node count')
 ns=[];ts=[]
 for i,node in enumerate(nodes):
  if type(node) is not list or not node or type(node[0]) is not str or node[0] not in ARITY or len(node)!=ARITY[node[0]]+1:raise StructureError('operation/arity')
  ats=[]
  for arg in node[1:]:
   if type(arg) is int:
    if not 0<=arg<i:raise StructureError('node reference must be backward')
    ats.append(ts[arg])
   elif type(arg) is str and arg in {'item','bins'}:ats.append('i32' if arg=='item' else 'vi64')
   elif type(arg) is str and len(arg)<=3 and re.fullmatch(r'c(?:0|[1-9][0-9]*)',arg):
    k=int(arg[1:])
    if k>=len(cs):raise StructureError('constant reference')
    ats.append(cs[k][0])
   else:raise StructureError('operand form')
  ts.append(infer(node[0],ats));ns.append(tuple(node))
 ret=d['return_node']
 if type(ret) is not int or not 0<=ret<len(nodes) or ts[ret]!='vf64':raise StructureError('return must reference float64 vector')
 canonical=json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
 return Program(description,tuple(cs),tuple(ns),tuple(ts),ret,hashlib.sha256(raw).hexdigest(),hashlib.sha256(canonical).hexdigest())
