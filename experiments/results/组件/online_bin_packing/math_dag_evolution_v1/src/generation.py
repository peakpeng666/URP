"""Fixed local rendering/tokenization/transport checks. No calls occur on import."""
import ast,base64,hashlib,json,math,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
SHARED=ROOT.parents[1]/'direct_route_generation_local_v2'
sys.path.insert(0,str(SHARED/'vendor/python'))
from jinja2.sandbox import ImmutableSandboxedEnvironment
from tokenizer_runtime import request as tokenize_process
from backend import run_once

def strict_json(raw):
 if type(raw) is bytes:raw=raw.decode('utf-8')
 def pairs(xs):
  out={}
  for k,v in xs:
   if k in out:raise ValueError('duplicate JSON key')
   out[k]=v
  return out
 def finite(x):
  v=float(x)
  if not math.isfinite(v):raise ValueError('nonfinite JSON value')
  return v
 def reject(x):raise ValueError('nonstandard JSON constant')
 return json.loads(raw,object_pairs_hook=pairs,parse_float=finite,parse_constant=reject)

def prepare_request(slot,prompt,directory,plan):
 directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=False)
 if len(prompt.encode())>32768:raise ValueError('prompt byte cap')
 template=(SHARED/'embedded_chat_template.jinja').read_text()
 if hashlib.sha256(template.encode()).hexdigest()!=plan['template']['sha256']:raise ValueError('template integrity')
 env=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True)
 rendered=env.from_string(template).render(messages=[{'role':'user','content':prompt}],tools=None,add_generation_prompt=True,enable_thinking=False)
 expected='<|im_start|>user\n'+prompt+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
 if rendered!=expected:raise ValueError('template framing changed')
 (directory/'problem.txt').write_text(prompt);(directory/'rendered.txt').write_text(rendered)
 command=[str(SHARED/'vendor/runtime/llama-b11387/llama-tokenize'),'-m',str(SHARED/'vendor/Qwen3-4B-Q4_K_M.gguf'),'-f',str(directory/'rendered.txt'),'--ids','--no-bos','--offline','-t','2','-tb','2']
 observation=tokenize_process(command)
 (directory/'tokenization.json').write_text(json.dumps(observation,indent=2)+'\n')
 if observation['returncode']!=0 or observation['termination'] is not None or observation['error'] is not None or not observation['reaped'] or not observation['cpu_evidence_complete']:raise ValueError('tokenizer process failure')
 ids=ast.literal_eval(base64.b64decode(observation['raw_stdout_base64']).decode('utf-8'))
 if type(ids) is not list or not ids or any(type(x) is not int or not 0<=x<151936 for x in ids):raise ValueError('token ID shape/range')
 if len(ids)>1660 or len(ids)+384+4>2048:raise ValueError('context overflow; no truncation')
 schema_path=ROOT/plan['decoding']['schema_file'];schema_raw=schema_path.read_bytes()
 if hashlib.sha256(schema_raw).hexdigest()!=plan['decoding']['schema_sha256']:raise ValueError('schema integrity')
 request=json.loads((ROOT/'interface_smoke_v2/request.json').read_bytes());request.update(prompt=ids,n_predict=384,seed=slot['seed'],json_schema=json.loads(schema_raw))
 raw=json.dumps(request,indent=2).encode()+b'\n'
 (directory/'input_token_ids.json').write_text(json.dumps(ids)+'\n');(directory/'request.json').write_bytes(raw)
 return raw,{'prompt_tokens':len(ids),'rendered_sha256':hashlib.sha256(rendered.encode()).hexdigest(),'request_sha256':hashlib.sha256(raw).hexdigest(),'tokenization':{k:observation[k] for k in ['pid','worker_cpu_seconds','worker_peak_rss_kib','wall_seconds','cleanup_seconds','reaped']}}

def decode(slot,raw,execution,prepared,plan):
 if execution.get('http_post_thread_finished') is not True or execution.get('cleanup',{}).get('direct_child_reaped') is not True:raise ValueError('unknown transport cleanup')
 if execution.get('process_status')=='timeout' and execution.get('post_requests_sent')==1:return {'status':'post_send_timeout','content':None}
 if execution.get('process_status')!='completed' or execution.get('http_status')!=200:raise ValueError('generation process/HTTP infrastructure failure')
 if len(raw)>1048576:raise ValueError('HTTP body cap')
 body=strict_json(raw)
 if type(body) is not dict:raise ValueError('HTTP envelope')
 if body.get('model')!=plan['command'][plan['command'].index('-m')+1]:raise ValueError('model path echo')
 want=dict(plan['sampling_base_profile'],seed=slot['seed']);settings=body.get('generation_settings')
 if type(settings) is not dict or set(settings)!=set(want):raise ValueError('effective setting keys')
 for key,value in want.items():
  if type(settings[key]) is not type(value) or settings[key]!=value:raise ValueError('effective setting mismatch: '+key)
 try:returned_hash=hashlib.sha256(body['prompt'].encode('utf-8')).hexdigest()
 except (KeyError,AttributeError,UnicodeError) as exc:raise ValueError('returned prompt') from exc
 if returned_hash!=prepared['rendered_sha256']:raise ValueError('returned prompt identity')
 if type(body.get('tokens_evaluated')) is not int or body['tokens_evaluated']!=prepared['prompt_tokens']:raise ValueError('input token count')
 count=body.get('tokens_predicted');tokens=body.get('tokens')
 if type(count) is not int or count<0 or type(tokens) is not list or len(tokens)!=count or any(type(x) is not int or not 0<=x<151936 for x in tokens):raise ValueError('output token evidence')
 if type(body.get('id_slot')) is not int or body['id_slot']!=0 or type(body.get('index')) is not int or body['index']!=0:raise ValueError('server slot identity')
 timings=body.get('timings')
 if type(timings) is not dict or type(timings.get('cache_n')) is not int or timings['cache_n']!=0 or timings.get('prompt_n')!=prepared['prompt_tokens'] or timings.get('predicted_n')!=count:raise ValueError('token timing/cache counts')
 for key in ['prompt_ms','predicted_ms']:
  value=timings.get(key)
  if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('timing evidence')
 content=body.get('content')
 if type(content) is not str:raise ValueError('content envelope type')
 content=content.encode('utf-8')
 metadata={'tokens_evaluated':body['tokens_evaluated'],'tokens_predicted':count,'stop_type':body.get('stop_type'),'truncated':body.get('truncated'),'timings':timings,'tokens_cached_current_slot':body.get('tokens_cached'),'content_sha256':hashlib.sha256(content).hexdigest()}
 if count>384:raise ValueError('output token ceiling violation')
 if body.get('truncated') is not False:raise ValueError('unexpected input truncation')
 if body.get('stop_type')=='limit':
  if count!=384 or body.get('stop') is not True:raise ValueError('premature or inconsistent limit stop')
  return {'status':'model_limit_stop','content':None,'metadata':metadata}
 if body.get('stop') is not True or body.get('stop_type')!='eos' or body.get('truncated') is not False or body.get('stopping_word')!='':raise ValueError('unknown completion termination')
 if not tokens or tokens[-1]!=151645 or 151645 in tokens[:-1]:raise ValueError('EOS evidence')
 if len(content)>32768:return {'status':'model_format_failure','content':None,'metadata':metadata}
 try:strict_json(content)
 except (ValueError,UnicodeError,RecursionError):return {'status':'model_format_failure','content':None,'metadata':metadata}
 return {'status':'completed_valid_transport','content':content,'metadata':metadata}
