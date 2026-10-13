"""Narrow study integrity, exact-data loading and observed/reserved accounting."""
import hashlib,json,pathlib,resource,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def bounded_json(path,limit=2000000):
 with pathlib.Path(path).open('rb') as f:raw=f.read(limit+1)
 if len(raw)>limit:raise ValueError('file size bound')
 return json.loads(raw)
def verify(expected,full=False):
 p=ROOT/'final_freeze.json'
 with p.open('rb') as f:raw=f.read(4000001)
 if len(raw)>4000000 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('approved study freeze mismatch')
 d=json.loads(raw)
 if sys.executable!=d['python_executable'] or sha(sys.executable)!=d['python_executable_sha256']:raise ValueError('actual interpreter')
 for rel,want in d['files'].items():
  if sha(ROOT/rel)!=want:raise ValueError('frozen study file changed: '+rel)
 actual=sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.py','.pyc','.so','.pyd'} and p.relative_to(ROOT).parts[0] not in {'runs','.authorization_uses'})
 if actual!=d['importable_files']:raise ValueError('study import inventory changed')
 for path,want in d.get('symlinks',{}).items():
  if not pathlib.Path(path).is_symlink() or str(pathlib.Path(path).readlink())!=want:raise ValueError('asset symlink changed')
 if full:
  for path,want in d['assets'].items():
   if sha(path)!=want:raise ValueError('shared asset changed: '+path)
  # Import only after the frozen own files/asset identities are checked.
  import importlib.util
  path=ROOT.parent/'math_dag_v1/src/integrity.py'
  spec=importlib.util.spec_from_file_location('unchanged_math_integrity',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  m.verify(d['math_evaluator_freeze'])
 return d

def load_cases(path,split,expected_ids):
 data=bounded_json(path,100000);cases=data['cases']
 if len(cases)!=4 or [c['id'] for c in cases]!=expected_ids or len(set(expected_ids))!=4:raise ValueError('frozen panel IDs/order')
 for c in cases:
  if c['split']!=split or c['n']!=128 or type(c['capacity']) is not int or c['capacity'] not in {100,500} or type(c['items']) is not list or len(c['items'])!=128 or any(type(v) is not int or not 1<=v<=100 for v in c['items']):raise ValueError('panel domain/type')
 return cases

class Budget:
 def __init__(self,plan,clock=time.monotonic,own=time.process_time,children=None):
  self.plan=plan;self.clock=clock;self.own=own;self.children=children or self.child_cpu
  self.start=clock();self.own_start=own();self.child_start=self.children();self.score_cpu=0.;self.score_wall=0.
 @staticmethod
 def child_cpu():
  r=resource.getrusage(resource.RUSAGE_CHILDREN);return r.ru_utime+r.ru_stime
 def measured(self):
  return {'supervisor_cpu_seconds':self.own()-self.own_start,'children_cpu_seconds':self.children()-self.child_start,'active_wall_seconds':self.clock()-self.start,'score_cpu_seconds':self.score_cpu,'score_wall_seconds':self.score_wall}
 def reserve(self,kind):
  m=self.measured();p=self.plan['aggregate_budgets'];debit=p['preparation_debit'];final=p['final_accounting_reserve']
  cpu,wall=(245,131) if kind=='model' else (20,31)
  if m['supervisor_cpu_seconds']+m['children_cpu_seconds']+debit['cpu_seconds']+cpu+final['cpu_seconds']>p['whole_study_observed_cpu_seconds']:raise RuntimeError('whole CPU reservation unavailable')
  if m['active_wall_seconds']+debit['active_wall_seconds']+wall+final['wall_seconds']>p['whole_study_active_wall_seconds']:raise RuntimeError('whole wall reservation unavailable')
  if kind=='score' and (self.score_cpu+20>p['scoring_observed_cpu_seconds'] or self.score_wall+31>p['scoring_observed_wall_seconds']):raise RuntimeError('score stage reservation unavailable')
 def score_mark(self):return self.own()+self.children(),self.clock()
 def score_charge(self,mark):
  self.score_cpu+=self.own()+self.children()-mark[0];self.score_wall+=self.clock()-mark[1]
 def terminal(self):
  m=self.measured();p=self.plan['aggregate_budgets'];debit=p['preparation_debit']
  m.update(charged_cpu_seconds=m['supervisor_cpu_seconds']+m['children_cpu_seconds']+debit['cpu_seconds'],charged_active_wall_seconds=m['active_wall_seconds']+debit['active_wall_seconds'])
  m['within_charged_budget']=m['charged_cpu_seconds']<=p['whole_study_observed_cpu_seconds'] and m['charged_active_wall_seconds']<=p['whole_study_active_wall_seconds'] and self.score_cpu<=p['scoring_observed_cpu_seconds'] and self.score_wall<=p['scoring_observed_wall_seconds']
  return m
