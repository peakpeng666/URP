"""Fixed22-slot study state machine. Callbacks are trusted, frozen adapters/test mocks.

No callback is supplied by a model or JSON graph. This module has no model,
network, numerical interpreter, source execution or automatic retry interface.
"""
import hashlib,json,pathlib
from policy import graph_identity,fitness,retain,parents,build_prompt,commitment,behavior_signature,structural_changes,validate_program,StructureError
ROOT=pathlib.Path(__file__).resolve().parents[1]

class Study:
 def __init__(self,plan,design,validation_ids,generate,score,load_validation,emit):
  self.plan=plan;self.design=design;self.design_ids=[c['id'] for c in design];self.validation_ids=validation_ids
  if len(self.design_ids)!=4 or len(set(self.design_ids))!=4 or len(validation_ids)!=4 or len(set(validation_ids))!=4 or set(self.design_ids)&set(validation_ids):raise ValueError('fixed split IDs')
  if self.design_ids!=plan['data']['design_case_ids'] or validation_ids!=plan['data']['validation_case_ids']:raise ValueError('protocol split ID/order binding')
  self.generate=generate;self.score=score;self.load_validation=load_validation;self.emit=emit
  self.sources={};self.requests=[dict(s,status='not_run',reason='scheduled') for s in plan['slots']]
  self.ledger=[]
  for s in plan['slots']:
   for split,ids in [('design',self.design_ids),('validation',validation_ids)]:
    for case in ids:self.ledger.append({'role':'candidate','source_id':s['slot_id'],'split':split,'case_id':case,'status':'not_run','reason':'scheduled' if split=='design' else 'not_selected_predeclared'})
  for source in ['ff','bf','published_formula']:
   for split,ids in [('design',self.design_ids),('validation',validation_ids)]:
    for case in ids:self.ledger.append({'role':'comparator','source_id':source,'split':split,'case_id':case,'status':'not_run','reason':'scheduled'})
  for arm in ['evolution','control']:
   for case in validation_ids:self.ledger.append({'role':'winner','arm':arm,'source_id':None,'split':'validation','case_id':case,'status':'not_run','reason':'awaiting_commitment'})
  if len(self.requests)!=22 or len(self.ledger)!=208:raise ValueError('fixed22/208 population')
  self.history=[];self.selected=None;self.selected_hash=None;self.halt=None;self.phase='prepared';self.score_dispatches=0;self.model_dispatches=0;self.measurements={};self.commitment_persisted=False
 def row(self,role,source,case,arm=None):
  found=[r for r in self.ledger if r['role']==role and r['case_id']==case and (r.get('arm')==arm if role=='winner' else r['source_id']==source)]
  if len(found)!=1:raise ValueError('ledger identity')
  return found[0]
 def score_cases(self,record,cases,role='candidate',arm=None):
  results=[]
  for case in cases:
   row=self.row(role,record['source_id'],case['id'],arm)
   row.update(status='started',reason=None,source_id=record['source_id'],raw_sha256=record['raw_sha256'],adapter_dispatched=False)
   try:
    self.emit('score_start',dict(row))
    if self.score_dispatches>=120:raise ValueError('score dispatch ceiling')
    self.score_dispatches+=1;row['adapter_dispatched']=True
    checked,evidence=self.score(record,case,self.score_dispatches-1)
    if checked.get('case_id')!=case['id']:raise ValueError('scoring adapter case mismatch')
    row.update(checked);row['evidence']=evidence
    if checked.get('status')=='completed_valid':
     identity=(record['graph_identity'],case['id'])
     signature={k:checked.get(k) for k in ['used_bins','L1','assignment','residuals','work_units','warning_events','warning_trace_sha256']}
     if identity in self.measurements and self.measurements[identity]!=signature:raise ValueError('conflicting deterministic graph/case observation')
     self.measurements.setdefault(identity,signature)
    results.append(checked)
   except Exception as exc:
    row.update(status='infrastructure_or_budget_stop',reason=type(exc).__name__+': '+str(exc));raise
   finally:
    if role=='winner' and record['origin']=='generated':
     linked=self.row('candidate',record['source_id'],case['id'])
     for link in linked['winner_links']:
      if link['arm']==arm:link.update(winner_case_status=row['status'],reason=row.get('reason'))
    try:self.emit('score_terminal',dict(row))
    except Exception as exc:row['terminal_persistence_error']=str(exc);raise
  return results
 def add_fixed(self,name,raw,order,origin):
  validate_program(raw)
  r={'source_id':name,'source_order':order,'origin':origin,'program_json':raw.decode(),'raw_sha256':hashlib.sha256(raw).hexdigest(),'graph_identity':graph_identity(raw),'fitness':None,'behavior_signature':None}
  self.sources[name]=r;return r
 def candidate(self,slot,population):
  row=next(r for r in self.requests if r['slot_id']==slot['slot_id'])
  chosen=[] if slot['operator']=='I1' else parents(population,slot['operator'])
  prompt=build_prompt(slot['operator'],chosen)
  row.update(status='started',reason=None,parent_source_ids=[p['source_id'] for p in chosen],prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),adapter_dispatched=False)
  try:
   self.emit('model_start',dict(row))
   if self.model_dispatches>=22:raise ValueError('model dispatch ceiling')
   self.model_dispatches+=1;row['adapter_dispatched']=True
   outcome=self.generate(slot,prompt,self.model_dispatches-1)
   row['generation_evidence']=outcome['evidence'];raw=outcome.get('content')
   if outcome['status']!='completed_valid_transport':
    if outcome['status'] not in {'model_format_failure','model_limit_stop','post_send_timeout'}:raise ValueError('generation infrastructure/unknown status: '+str(outcome['status']))
    row.update(status='generation_failed',reason=outcome['status'])
    for case in self.design:self.row('candidate',slot['slot_id'],case['id']).update(reason='generation_failed')
    return None
   if type(raw) is not bytes:raise ValueError('generation adapter content type')
   row['raw_sha256']=hashlib.sha256(raw).hexdigest()
   try:validate_program(raw)
   except StructureError as exc:
    row.update(status='dag_rejected',reason=type(exc).__name__+': '+str(exc))
    for case in self.design:self.row('candidate',slot['slot_id'],case['id']).update(reason='dag_rejected')
    return None
   record=self.add_fixed(slot['slot_id'],raw,2+self.plan['slots'].index(slot),'generated')
   record['operator_changes']=[structural_changes(p['program_json'].encode(),raw) for p in chosen]
   record['design_results']=self.score_cases(record,self.design)
   record['fitness']=fitness(record['design_results'],self.design_ids);record['behavior_signature']=behavior_signature(record['design_results'])
   row.update(status='design_eligible' if record['fitness'] is not None else 'design_unresolved_or_invalid',graph_identity=record['graph_identity'],fitness=record['fitness'])
   return record
  except Exception as exc:
   row.update(status='infrastructure_or_budget_stop',reason=type(exc).__name__+': '+str(exc));raise
  finally:
   try:self.emit('model_terminal',dict(row))
   except Exception as exc:row['terminal_persistence_error']=str(exc);raise
 def run(self):
  try:
   self.phase='seed_design';initial=[]
   for i,name in enumerate(['ff','bf']):
    r=self.add_fixed(name,(ROOT/'seeds'/(name+'.json')).read_bytes(),i,'handwritten_seed')
    r['design_results']=self.score_cases(r,self.design,'comparator');r['fitness']=fitness(r['design_results'],self.design_ids);r['behavior_signature']=behavior_signature(r['design_results'])
    if r['fitness'] is None:raise ValueError('fixed seed did not complete')
    initial.append(r)
   self.phase='shared_initialization'
   for slot in self.plan['slots'][:2]:
    r=self.candidate(slot,[])
    if r is not None:initial.append(r)
   evolution=retain(initial);control=retain(initial)
   if len(evolution)!=2:raise ValueError('insufficient initial parents')
   self.history.append({'generation':0,'evolution':[r['source_id'] for r in evolution],'control':[r['source_id'] for r in control]})
   for generation in [1,2]:
    self.phase='generation_'+str(generation)
    snapshot=list(evolution);evo_new=[];control_new=[]
    self.emit('generation_snapshot',{'generation':generation,'parents':[r['source_id'] for r in snapshot]})
    for slot in [x for x in self.plan['slots'] if x['generation']==generation]:
     r=self.candidate(slot,snapshot if slot['arm']=='evolution' else [])
     if r is not None:(evo_new if slot['arm']=='evolution' else control_new).append(r)
    evolution=retain(evolution+evo_new);control=retain(control+control_new)
    if len(evolution)!=2 or len(control)!=2:raise ValueError('insufficient retained parents')
    self.history.append({'generation':generation,'evolution':[r['source_id'] for r in evolution],'control':[r['source_id'] for r in control]})
   self.phase='winner_commitment';self.selected,self.selected_hash=commitment(evolution,control)
   # Trusted sink must durably create the commitment before this call returns.
   self.emit('winner_commitment',{'selected':self.selected,'sha256':self.selected_hash})
   self.commitment_persisted=True
   for arm in ['evolution','control']:
    r=self.sources[self.selected[arm]['source_id']]
    for case_id in self.validation_ids:
     self.row('winner',r['source_id'],case_id,arm).update(source_id=r['source_id'],raw_sha256=r['raw_sha256'],reason='committed_winner_awaiting_validation')
     if r['origin']=='generated':
      linked=self.row('candidate',r['source_id'],case_id);linked.update(status='linked_winner_role',reason=None)
      linked.setdefault('winner_links',[]).append({'arm':arm,'winner_case_status':'not_run','reason':'awaiting_validation'})
   self.phase='validation';validation=self.load_validation()
   if [c['id'] for c in validation]!=self.validation_ids:raise ValueError('validation ID/order')
   for arm in ['evolution','control']:
    r=self.sources[self.selected[arm]['source_id']];results=self.score_cases(r,validation,'winner',arm)
   for name in ['ff','bf']:self.score_cases(self.sources[name],validation,'comparator')
   self.phase='published_reference'
   p=self.add_fixed('published_formula',(ROOT.parent/'math_dag_v1/fixtures/programs/published_eoh.json').read_bytes(),24,'fixed_published_reference')
   self.score_cases(p,self.design+validation,'comparator')
   self.phase='completed'
  except Exception as exc:
   self.halt={'phase':self.phase,'type':type(exc).__name__,'message':str(exc)};self.phase='incomplete'
   for row in self.requests:
    if row['status']=='not_run':row['reason']='study_stopped'
   for row in self.ledger:
    if row['status']=='not_run' and row['reason']!='not_selected_predeclared':row['reason']='study_stopped'
    for link in row.get('winner_links',[]):
     if link['winner_case_status']=='not_run':link['reason']='study_stopped'
  return {'state':self.phase,'halt':self.halt,'requests':self.requests,'ledger':self.ledger,'sources':self.sources,'history':self.history,'selected':self.selected,'selected_hash':self.selected_hash,'commitment_persisted':self.commitment_persisted,'model_adapter_calls':self.model_dispatches,'scoring_adapter_calls':self.score_dispatches}
