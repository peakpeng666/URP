"""Predeclared descriptive summaries; no selection changes or extra evaluations."""
from fractions import Fraction
from policy import rank_key

def aggregate(rows):
 if len(rows)!=4 or any(r.get('status')!='completed_valid' for r in rows):return None
 used=sum(r['used_bins'] for r in rows);lower=sum(r['L1'] for r in rows)
 f=Fraction(used-lower,lower)
 return {'sum_used_bins':used,'sum_L1':lower,'excess_numerator':f.numerator,'excess_denominator':f.denominator,'L1_excess':float(f)}

def summarize(state,dispatches):
 if len(state.get('requests',[]))!=22 or len(state.get('ledger',[]))!=208:return {'scope':'incomplete prelaunch evidence','complete':False}
 sources=state['sources'];arms={};by_slot={r['slot_id']:r for r in state['requests']}
 for arm in ['evolution','control']:
  requests=[r for r in state['requests'] if r['arm'] in {'shared',arm}]
  ids={r['slot_id'] for r in requests};records=[sources[x] for x in ids if x in sources];eligible=[r for r in records if r.get('fitness') is not None]
  best=min(eligible,key=rank_key) if eligible else None
  selected=(state.get('selected') or {}).get(arm)
  costs=[d for d in dispatches if d.get('kind')=='model' and d.get('slot_id') in ids]
  model_cpu=[];model_wall=[];input_tokens=[];output_tokens=[]
  for r in requests:
   evidence=r.get('generation_evidence',{});e=evidence.get('execution');m=evidence.get('metadata')
   if e is not None:model_cpu.append(e['child_user_cpu_seconds']+e['child_system_cpu_seconds']);model_wall.append(e['whole_process_lifetime_wall_seconds'])
   if m is not None and type(m.get('tokens_evaluated')) is int:input_tokens.append(m['tokens_evaluated'])
   if m is not None and type(m.get('tokens_predicted')) is int:output_tokens.append(m['tokens_predicted'])
  validation=[r for r in state['ledger'] if r['role']=='winner' and r['arm']==arm]
  arms[arm]={'scheduled_opportunities':12,'shared_initialization_opportunities':2,'observed_post_requests':sum(x.get('post_requests_sent',0) for x in costs),'not_run':sum(r['status']=='not_run' for r in requests),'request_statuses':{status:sum(r['status']==status for r in requests) for status in sorted({r['status'] for r in requests})},'dag_admitted_records':len(records),'design_eligible_records':len(eligible),'distinct_graph_representations':len({r['graph_identity'] for r in records}),'distinct_complete_design_behaviors':len({r['behavior_signature'] for r in eligible}),'seed_inclusive_selected':selected,'generated_only_best_design':None if best is None else {k:best[k] for k in ['source_id','graph_identity','fitness']},'winner_validation':aggregate(validation),'validation_case_outcomes':[{k:r.get(k) for k in ['case_id','status','used_bins','L1','reason']} for r in validation],'observed_server_cpu_seconds':sum(model_cpu),'server_cpu_records':len(model_cpu),'observed_server_lifetime_wall_seconds':sum(model_wall),'known_input_tokens':sum(input_tokens),'input_token_records':len(input_tokens),'known_output_tokens':sum(output_tokens),'output_token_records':len(output_tokens),'unknown_token_rows':12-len(output_tokens)}
 comparisons={}
 for source in ['ff','bf','published_formula']:
  comparisons[source]={split:aggregate([r for r in state['ledger'] if r['role']=='comparator' and r['source_id']==source and r['split']==split]) for split in ['design','validation']}
 for arm in arms:
  w=arms[arm]['winner_validation'];arms[arm]['validation_bins_minus_seed']={seed:None if w is None or comparisons[seed]['validation'] is None else w['sum_used_bins']-comparisons[seed]['validation']['sum_used_bins'] for seed in ['ff','bf']}
 pairs=[]
 for pair in range(10):
  rows=[r for r in state['requests'] if r.get('pair')==pair]
  pairs.append({'pair':pair,'rows':[{k:r.get(k) for k in ['slot_id','arm','status','seed','adapter_dispatched','reason']} for r in rows],'both_adapters_dispatched':all(r.get('adapter_dispatched') is True for r in rows)})
 feedback=[r for r in state['requests'] if r['arm']=='evolution' and r['generation']==2]
 return {'complete':state['state']=='completed','physical_scheduled_requests':22,'shared_opportunities_not_summable_across_arms':True,'arms':arms,'fixed_comparators':comparisons,'pairs':pairs,'generation2_operator_inputs_with_generation1_generated_parent':sum(any(p.startswith('g1_') for p in r.get('parent_source_ids',[])) for r in feedback),'seed_inclusive_winner_is_not_generated_success':True,'scope':'One small seeded two-generation mechanism comparison; descriptive only, no independent replication/significance/novelty or original-EoH claims. Equal request opportunities are not equal token/CPU costs.'}
