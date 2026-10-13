"""One fixed-data schema interface smoke; default verifies only, never inference."""
import argparse,hashlib,json,math,sys
from pathlib import Path
H=Path(__file__).resolve().parent
C=H.parents[2]/'direct_route_generation_local_v2'
sys.path.insert(0,str(C/'formal_v2'));from score_local import strict_json

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(4*1024**2),b''):h.update(c)
 return h.hexdigest()

def value_equal(a,b):
 if type(a)in (int,float) and type(b)in (int,float):return a==b
 if type(a)is not type(b):return False
 if type(a)is dict:return set(a)==set(b) and all(value_equal(a[k],b[k]) for k in a)
 if type(a)is list:return len(a)==len(b) and all(value_equal(x,y) for x,y in zip(a,b))
 return a==b

def verify_assets(f):
 for p,want in f['asset_sha256'].items():
  if sha(H/p)!=want:raise ValueError('asset_changed:'+p)

def verify_sources(f):
 for p,want in f['file_sha256'].items():
  if sha(H/p)!=want:raise ValueError('source_changed:'+p)

def assess(directory):
 cfg=strict_json((H/'protocol.json').read_bytes());request=strict_json((H/'request.json').read_bytes());target=strict_json((H/'target.json').read_bytes())
 execution=strict_json((directory/'result.json').read_bytes());stderr=(directory/'server_stderr.log').read_text(errors='replace');errors=[]
 result={'purpose':'fixed_data_schema_interface_smoke_not_candidate_design','model_calls':execution['post_requests_sent'],'graph_interpreter_calls':0,'fitness_calls':0,'formal_candidate_calls':0,'process_status':execution['process_status'],'errors':errors,'content_matches_target':False,'passed':False,'schema_conversion_warning':False,'native_grammar_sha256':None}
 if 'json schema conversion was incomplete' in stderr.lower():errors.append('schema_conversion_incomplete');result['schema_conversion_warning']=True
 if execution.get('http_post_thread_finished')is not True:errors.append('http_writer_not_finished');return result
 if execution['process_status']!='completed' or execution['http_status']!=200:errors.append('transport_or_process_failure');return result
 try:
  response=strict_json((directory/'response_body.json').read_bytes());content=response['content'];content_bytes=content.encode('utf-8',errors='strict');parsed=strict_json(content)
 except (ValueError,UnicodeError,KeyError,TypeError,AttributeError) as e:errors.append('response_or_content_invalid:'+str(e));return result
 result['content_sha256']=hashlib.sha256(content_bytes).hexdigest();result['content_matches_target']=value_equal(parsed,target)
 if not result['content_matches_target']:errors.append('fixed_target_value_mismatch')
 if response.get('stop')is not True or response.get('stop_type')!='eos':errors.append('not_eos')
 if response.get('truncated')is not False:errors.append('truncated_or_missing')
 if response.get('model')!=cfg['command'][cfg['command'].index('-m')+1]:errors.append('model_path_mismatch')
 if type(response.get('id_slot'))is not int or response['id_slot']!=0:errors.append('slot_mismatch')
 if type(response.get('index'))is not int or response['index']!=0:errors.append('response_index_mismatch')
 count=response.get('tokens_predicted');ids=response.get('tokens')
 if type(count)is not int or not 1<=count<=128:errors.append('invalid_output_count')
 if type(ids)is not list or not ids or len(ids)!=count or not all(type(v)is int and 0<=v<151936 for v in ids):errors.append('invalid_output_ids')
 elif ids[-1]!=151645 or 151645 in ids[:-1]:errors.append('eos_token_mismatch')
 if type(response.get('tokens_evaluated'))is not int or response['tokens_evaluated']!=cfg['prompt_tokens']:errors.append('input_token_count_mismatch')
 try:
  if hashlib.sha256(response['prompt'].encode('utf-8')).hexdigest()!=sha(H/'rendered.txt'):errors.append('returned_prompt_mismatch')
 except (KeyError,UnicodeError,AttributeError):errors.append('returned_prompt_invalid')
 settings=response.get('generation_settings');expected=cfg['expected_generation_settings_except_grammar']
 if type(settings)is not dict:errors.append('settings_missing')
 else:
  if set(settings)!=set(expected)|{'grammar'}:errors.append('settings_keys_mismatch')
  for key,want in expected.items():
   if key not in settings or type(settings[key])is not type(want) or settings[key]!=want:errors.append('setting_mismatch:'+key)
  grammar=settings.get('grammar')
  if type(grammar)is not str or not grammar.strip():errors.append('native_effective_grammar_empty')
  else:
   result['native_grammar_sha256']=hashlib.sha256(grammar.encode()).hexdigest();(directory/'effective_grammar.gbnf').write_text(grammar)
 timings=response.get('timings')
 if type(timings)is not dict or timings.get('cache_n')!=0 or timings.get('prompt_n')!=cfg['prompt_tokens'] or timings.get('predicted_n')!=count:errors.append('timing_count_or_cache_mismatch')
 result.update(stop_type=response.get('stop_type'),tokens_predicted=count,tokens_evaluated=response.get('tokens_evaluated'),timings=timings,tokens_cached_current_slot=response.get('tokens_cached'),raw_response_sha256=sha(directory/'response_body.json'),unmodified_content_saved=(directory/'content.txt').read_bytes()==content_bytes)
 if not result['unmodified_content_saved']:errors.append('saved_content_mismatch')
 result['passed']=not errors
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute-approved',action='store_true');a=p.parse_args()
 f=strict_json((H/'freeze.json').read_bytes());verify_sources(f)
 print('sources verified; no model call yet',flush=True)
 if not a.execute_approved:return
 verify_assets(f)
 # Import by exact file to avoid taking the similarly named CVRP module.
 import importlib.util
 spec=importlib.util.spec_from_file_location('dag_smoke_backend',H/'local_backend.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 directory=H/'runs'/'attempt01';result=module.run_once(0,(H/'request.json').read_bytes(),directory)
 assessment=assess(directory)
 try:verify_sources(f);verify_assets(f);assessment['post_hashes_match']=True
 except Exception as e:assessment['post_hashes_match']=False;assessment['passed']=False;assessment['errors'].append('post_integrity:'+repr(e))
 (directory/'assessment.json').write_text(json.dumps(assessment,indent=2,allow_nan=False)+'\n');print(json.dumps(assessment,indent=2,allow_nan=False))

if __name__=='__main__':main()
