"""Response checks copied narrowly from accepted22-call transport contract."""
import hashlib,math,re
from measurement import strict_json
def decode(slot,raw,execution,prepared,plan):
 if execution.get('http_post_thread_finished') is not True or execution.get('cleanup',{}).get('direct_child_reaped') is not True:raise ValueError('unknown transport cleanup')
 if type(execution.get('server_pid'))is not int or execution['server_pid']<=0:raise ValueError('missing server PID')
 limits=execution.get('server_effective_limits_text','')
 for label,want in [('Max cpu time',240),('Max file size',1048576),('Max address space',4294967296),('Max core file size',0)]:
  if not re.search(re.escape(label)+r'\s+'+str(want)+r'\s+'+str(want)+r'\s',limits):raise ValueError('effective server limits: '+label)
 if execution.get('process_status')=='timeout' and execution.get('post_requests_sent')==1:return {'status':'post_send_timeout','content':None}
 if execution.get('process_status')!='completed' or execution.get('http_status')!=200 or execution.get('server_exit_code')!=0:raise ValueError('generation process/HTTP infrastructure failure')
 if len(raw)>1048576:raise ValueError('HTTP body cap')
 body=strict_json(raw)
 if type(body) is not dict:raise ValueError('HTTP envelope')
 if body.get('model')!=plan['command'][plan['command'].index('-m')+1]:raise ValueError('model path echo')
 settings=body.get('generation_settings')
 grammar=settings.get('grammar') if type(settings)is dict else None
 if type(grammar)is not str or not grammar.strip() or len(grammar.encode())>200000:raise ValueError('missing/oversized native grammar')
 want=dict(plan['sampling_base_profile'],seed=slot['seed'],grammar=grammar)
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
 metadata={'tokens_evaluated':body['tokens_evaluated'],'tokens_predicted':count,'stop_type':body.get('stop_type'),'truncated':body.get('truncated'),'timings':timings,'tokens_cached_current_slot':body.get('tokens_cached'),'content_sha256':hashlib.sha256(content).hexdigest(),'grammar_sha256':hashlib.sha256(grammar.encode()).hexdigest()}
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
