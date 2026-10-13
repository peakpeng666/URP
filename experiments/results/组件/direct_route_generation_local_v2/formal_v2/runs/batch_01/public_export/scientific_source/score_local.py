"""Pure offline local-v2 scoring. No inference and no content repair."""
import hashlib,json,math,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
# Public packaging: the unchanged checker package is adjacent to this module.
from urp_cvrp.instance import from_dict
from urp_cvrp.checker import check_solution

def unique(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ValueError('duplicate_json_key')
  out[k]=v
 return out

def finite_float(text):
 v=float(text)
 if not math.isfinite(v):raise ValueError('nonfinite_number')
 return v

def bad_constant(text):raise ValueError('nonfinite_constant')

def strict_json(raw):
 if type(raw)is bytes:raw=raw.decode('utf-8',errors='strict')
 return json.loads(raw,object_pairs_hook=unique,parse_constant=bad_constant,parse_float=finite_float)

def f32(v):return struct.unpack('f',struct.pack('f',v))[0]

def evaluate(slot, raw_http, http_status, process_status, instance_raw):
 """slot is trusted frozen config; HTTP bytes are untrusted model transport."""
 instance=from_dict(instance_raw);reference=slot['reference']
 refcheck=check_solution(instance,{'routes':reference['routes'],'reported_cost':reference['cost']})
 if not refcheck.accepted:raise ValueError('invalid_frozen_reference')
 result={'slot_index':slot['slot_index'],'instance_id':instance.instance_id,'format':slot['format'],
   'process_status':process_status,'http_status':http_status,'raw_http_sha256':hashlib.sha256(raw_http).hexdigest(),
   'transport_valid':False,'content_json_valid':False,'route_feasible':False,'fallback_used':True,
   'model_cost':None,'gap_pct':None,'delivered_cost':refcheck.recomputed_cost,'delivered_routes':reference['routes'],
   'errors':[],'content_sha256':None,'stop_type':None,'tokens_predicted':None,'tokens_evaluated':None}
 def fail(error):result['errors'].append(error);return result
 if process_status!='completed':return fail('process:'+process_status)
 if type(http_status)is not int or http_status!=200:return fail('http_not_200')
 if len(raw_http)>1048576:return fail('http_body_too_large')
 try:body=strict_json(raw_http)
 except (ValueError,UnicodeError,RecursionError) as e:return fail('http_json:'+str(e))
 if type(body)is not dict:return fail('http_body_not_object')
 if body.get('model')!=slot['model_path']:return fail('model_path_mismatch')
 content=body.get('content')
 if type(content)is not str:return fail('content_not_string')
 try:content_bytes=content.encode('utf-8',errors='strict')
 except UnicodeError:return fail('content_not_valid_unicode')
 result['content_sha256']=hashlib.sha256(content_bytes).hexdigest()
 result['stop_type']=body.get('stop_type');result['tokens_predicted']=body.get('tokens_predicted');result['tokens_evaluated']=body.get('tokens_evaluated')
 # Inference control metadata is outside model content and must match the freeze.
 if body.get('stop')is not True:return fail('stop_not_true')
 if body.get('stop_type')!='eos':return fail('finish_not_eos')
 if body.get('truncated')is not False:return fail('truncated_or_missing_flag')
 if body.get('stopping_word')!='':return fail('unexpected_or_missing_stopping_word')
 if type(body.get('tokens_cached'))is not int or body['tokens_cached']<0:return fail('invalid_current_slot_token_count')
 try:returned_prompt_hash=hashlib.sha256(body['prompt'].encode('utf-8',errors='strict')).hexdigest()
 except (KeyError,AttributeError,UnicodeError):return fail('invalid_returned_prompt')
 if returned_prompt_hash!=slot['files']['rendered.txt']:return fail('returned_prompt_mismatch')
 count=body.get('tokens_predicted');tokens=body.get('tokens')
 if type(count)is not int or not 1<=count<=512:return fail('invalid_output_token_count')
 if type(tokens)is not list or len(tokens)!=count or not all(type(t)is int for t in tokens):return fail('invalid_output_token_ids')
 if any(t<0 or t>=slot['vocab_size'] for t in tokens):return fail('token_id_out_of_vocab')
 if tokens[-1]!=slot['eos_token_id']:return fail('last_token_not_frozen_eos')
 if slot['eos_token_id'] in tokens[:-1]:return fail('early_eos_in_generated_tokens')
 if type(body.get('id_slot'))is not int or body['id_slot']!=slot['expected_id_slot']:return fail('unexpected_slot_id')
 if type(body.get('index'))is not int or body['index']!=slot['expected_response_index']:return fail('unexpected_response_index')
 if type(body.get('tokens_evaluated'))is not int or body['tokens_evaluated']!=slot['prompt_tokens']:return fail('prompt_token_count_mismatch')
 settings=body.get('generation_settings')
 if type(settings)is not dict:return fail('generation_settings_missing')
 if set(settings)!=set(slot['effective_settings']):return fail('generation_settings_key_set_mismatch')
 for key,want in slot['effective_settings'].items():
  if key not in settings or type(settings[key])is not type(want):return fail('setting_type_or_key:'+key)
  if settings[key]!=want:return fail('setting_mismatch:'+key)
 timings=body.get('timings')
 if type(timings)is not dict or type(timings.get('cache_n'))is not int or timings['cache_n']!=0:return fail('nonzero_or_missing_prompt_cache_reuse')
 if type(timings.get('prompt_n'))is not int or timings['prompt_n']!=slot['prompt_tokens']:return fail('timing_prompt_count_mismatch')
 if type(timings.get('predicted_n'))is not int or timings['predicted_n']!=count:return fail('timing_generated_count_mismatch')
 for key in ['prompt_ms','predicted_ms']:
  value=timings.get(key)
  if type(value)not in (int,float):return fail('invalid_timing:'+key)
  try:valid=math.isfinite(value) and value>=0
  except (OverflowError,ValueError):valid=False
  if not valid:return fail('invalid_timing:'+key)
 result['runtime_timings']=timings
 result['tokens_cached_current_slot']=body['tokens_cached']
 result['transport_valid']=True
 if len(content.encode('utf-8'))>65536:return fail('content_too_large')
 try:output=strict_json(content)
 except (ValueError,UnicodeError,RecursionError) as e:return fail('content_json:'+str(e))
 if type(output)is not dict or set(output)!={'routes'}:return fail('exact_routes_key_required')
 result['content_json_valid']=True
 checked=check_solution(instance,output);result['checker_raw']=checked.to_dict()
 result['route_feasible']=checked.feasible
 result['errors']=[e for e in checked.errors if e!='invalid_reported_cost']
 if checked.feasible:
  result.update(fallback_used=False,model_cost=checked.recomputed_cost,
    gap_pct=100*(checked.recomputed_cost/refcheck.recomputed_cost-1),
    delivered_cost=checked.recomputed_cost,delivered_routes=output['routes'])
 return result

def summarize(rows):
 if len(rows)!=8 or sorted(r['slot_index'] for r in rows)!=list(range(8)):raise ValueError('eight_unique_scheduled_slots_required')
 groups={}
 for fmt in ['json','table']:
  subset=[r for r in rows if r['format']==fmt]
  if len(subset)!=4:raise ValueError('four_each_format_required')
  valid=[r for r in subset if r['route_feasible']]
  groups[fmt]={'scheduled':4,'attempted':sum(r['process_status']!='not_run' for r in subset),
   'route_feasible_count':len(valid),'scheduled_feasibility_rate':len(valid)/4,
   'fallback_rate':sum(r['fallback_used'] for r in subset)/4,
   'conditional_valid_mean_gap_pct':sum(r['gap_pct'] for r in valid)/len(valid) if valid else None,
   'hybrid_scheduled_mean_gap_pct':sum(r['gap_pct'] if r['route_feasible'] else 0 for r in subset)/4}
 pairs=[]
 for iid in sorted({r['instance_id'] for r in rows}):
  pair={r['format']:r for r in rows if r['instance_id']==iid}
  if len(pair)!=2:raise ValueError('instance_pair_missing')
  if all(v['route_feasible'] for v in pair.values()):pairs.append({'instance_id':iid,'table_minus_json_gap_points':pair['table']['gap_pct']-pair['json']['gap_pct']})
 return {'complete_eight_attempts':all(r['process_status']!='not_run' for r in rows),'formats':groups,'both_feasible_pair_count':len(pairs),'paired_differences':pairs,'not_run_count':sum(r['process_status']=='not_run' for r in rows)}
