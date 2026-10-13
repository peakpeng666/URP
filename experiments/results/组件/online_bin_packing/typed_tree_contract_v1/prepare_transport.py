"""Offline installed converter and tokenizer only. Never starts inference."""
import ast,base64,hashlib,json,pathlib,resource,sys,time
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'transport'))
from tokenizer_runtime import request
from typed_tree import compile_tree
SHARED=ROOT.parents[1]/'direct_route_generation_local_v2'
sys.path.insert(0,str(SHARED/'vendor/python'))
from jinja2.sandbox import ImmutableSandboxedEnvironment

def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 start=time.monotonic();cpu=time.process_time();child=resource.getrusage(resource.RUSAGE_CHILDREN);plan=json.loads((ROOT/'transport_protocol.json').read_text())
 command=[plan['command'][0],'--json-schema-file',str(ROOT/'generation_schema.json'),'--help','--offline']
 converter=request(command);save(ROOT/'offline/converter.json',dict(command=command,**converter))
 stderr=base64.b64decode(converter['raw_stderr_base64']).decode(errors='replace')
 if converter['returncode']!=0 or converter['error'] or converter['termination'] or not converter['reaped'] or stderr.strip():raise ValueError('offline converter failed or warned: '+stderr[:500])
 prompts=json.loads((ROOT/'prompts.json').read_text());slots=[]
 template=(SHARED/'embedded_chat_template.jinja').read_text()
 if hashlib.sha256(template.encode()).hexdigest()!=plan['template']['sha256']:raise ValueError('template identity')
 env=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True)
 base=json.loads((ROOT.parent/'math_dag_interface_v2_1/requests/00/request.json').read_text())
 for i,p in enumerate(prompts):
  d=ROOT/'requests'/('%02d'%i);d.mkdir(parents=True,exist_ok=False)
  prompt=p['prompt'];rendered=env.from_string(template).render(messages=[{'role':'user','content':prompt}],tools=None,add_generation_prompt=True,enable_thinking=False)
  (d/'problem.txt').write_text(prompt);(d/'rendered.txt').write_text(rendered)
  cmd=[str(SHARED/'vendor/runtime/llama-b11387/llama-tokenize'),'-m',str(SHARED/'vendor/Qwen3-4B-Q4_K_M.gguf'),'-f',str(d/'rendered.txt'),'--ids','--no-bos','--offline','-t','2','-tb','2']
  obs=request(cmd);save(d/'tokenization.json',dict(command=cmd,**obs))
  if obs['returncode']!=0 or obs['error'] or obs['termination'] or not obs['reaped']:raise ValueError('tokenizer failure')
  ids=ast.literal_eval(base64.b64decode(obs['raw_stdout_base64']).decode())
  if not ids or any(type(x)is not int or not 0<=x<151936 for x in ids) or len(ids)>1660 or len(ids)+384+4>2048:raise ValueError('context overflow/type; no truncation')
  seed=2026100800+i;req=dict(base,prompt=ids,seed=seed,json_schema=json.loads((ROOT/'generation_schema.json').read_text()))
  save(d/'request.json',req);save(d/'token_ids.json',ids)
  slots.append({'id':p['id'],'seed':seed,'request_file':str((d/'request.json').relative_to(ROOT)),'request_sha256':sha(d/'request.json'),'rendered_sha256':sha(d/'rendered.txt'),'prompt_tokens':len(ids)})
 _,target=compile_tree((ROOT/'data/fixed_tree.json').read_bytes());save(ROOT/'data/fixed_target.json',target)
 after=resource.getrusage(resource.RUSAGE_CHILDREN)
 report={'slots':slots,'model_calls':0,'score_calls':0,'converter_accepted':True,'converter_grammar_not_emitted':True,'cpu_seconds':time.process_time()-cpu+after.ru_utime+after.ru_stime-child.ru_utime-child.ru_stime,'wall_seconds':time.monotonic()-start}
 save(ROOT/'transport_preparation.json',report);print(json.dumps(report))
if __name__=='__main__':main()
