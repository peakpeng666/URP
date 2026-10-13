"""Deterministic fake transport/worker tests; no external process or POST."""
import contextlib,copy,hashlib,importlib.util,io,json,pathlib,shutil,sys,tempfile,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from test_measurement import fake,RAW,CASES
from transport_check import decode
spec=importlib.util.spec_from_file_location('diag_runner',ROOT/'run_diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PLAN=json.loads((ROOT/'protocol.json').read_text());TP=json.loads((ROOT/'transport_protocol.json').read_text());SLOTS=json.loads((ROOT/'transport_preparation.json').read_text())['slots']
LIMITS='Max cpu time 240 240 seconds\nMax file size 1048576 1048576 bytes\nMax address space 4294967296 4294967296 bytes\nMax core file size 0 0 bytes\n'
def execution():return {'http_post_thread_finished':True,'cleanup':{'direct_child_reaped':True},'server_pid':42,'server_effective_limits_text':LIMITS,'process_status':'completed','http_status':200,'server_exit_code':0,'post_requests_sent':1}
def body(slot,content=RAW.decode(),stop='eos',count=81):
 prompt=(ROOT/slot['request_file']).parent/'rendered.txt'
 if not prompt.exists():prompt=(ROOT/slot['request_file']).parent/'prompt.rendered.txt'
 text=prompt.read_text()
 return {'content':content,'model':TP['command'][TP['command'].index('-m')+1],'generation_settings':dict(TP['sampling_base_profile'],seed=slot['seed'],grammar='root ::= "mock"'),'prompt':text,'tokens_evaluated':slot['prompt_tokens'],'tokens_predicted':count,'tokens':[99]*(count-1)+([151645] if stop=='eos' else [99]),'id_slot':0,'index':0,'timings':{'cache_n':0,'prompt_n':slot['prompt_tokens'],'predicted_n':count,'prompt_ms':1.0,'predicted_ms':1.0},'stop':True,'stop_type':stop,'truncated':False,'stopping_word':''}
class TransportTests(unittest.TestCase):
 def test_success(self):self.assertEqual(decode(SLOTS[0],json.dumps(body(SLOTS[0])).encode(),execution(),SLOTS[0],TP)['status'],'completed_valid_transport')
 def test_exact_cap_ordinary(self):self.assertEqual(decode(SLOTS[0],json.dumps(body(SLOTS[0],stop='limit',count=384)).encode(),execution(),SLOTS[0],TP)['status'],'model_limit_stop')
 def test_over_cap_infrastructure(self):
  with self.assertRaises(ValueError):decode(SLOTS[0],json.dumps(body(SLOTS[0],stop='limit',count=385)).encode(),execution(),SLOTS[0],TP)
 def test_missing_limits(self):
  e=execution();e['server_effective_limits_text']=''
  with self.assertRaises(ValueError):decode(SLOTS[0],json.dumps(body(SLOTS[0])).encode(),e,SLOTS[0],TP)
 def test_unclean_exit(self):
  e=execution();e['server_exit_code']=1
  with self.assertRaises(ValueError):decode(SLOTS[0],json.dumps(body(SLOTS[0])).encode(),e,SLOTS[0],TP)
 def test_empty_grammar(self):
  b=body(SLOTS[0]);b['generation_settings']['grammar']=''
  with self.assertRaises(ValueError):decode(SLOTS[0],json.dumps(b).encode(),execution(),SLOTS[0],TP)
 def test_wrong_echo(self):
  b=body(SLOTS[0]);b['generation_settings']['seed']+=1
  with self.assertRaises(ValueError):decode(SLOTS[0],json.dumps(b).encode(),execution(),SLOTS[0],TP)
class RunnerTests(unittest.TestCase):
 def run_fake(self,mode='good'):
  calls=[];score=[];td=tempfile.TemporaryDirectory();base=pathlib.Path(td.name);p=base/'study';p.mkdir();
  for name in ['data','requests']:shutil.copytree(ROOT/name,p/name)
  for name in ['transport_preparation.json','transport_protocol.json']:shutil.copyfile(ROOT/name,p/name)
  seeds=base/'math_dag_evolution_v1/seeds';seeds.mkdir(parents=True)
  for name in ['ff.json','bf.json']:shutil.copyfile(ROOT.parent/'math_dag_evolution_v1/seeds'/name,seeds/name)
  def backend(index,request,directory):
   calls.append(index);directory.mkdir(parents=True);b=body(SLOTS[index])
   if mode=='caps':b=body(SLOTS[index],content='{',stop='limit',count=384)
   if mode=='grammar_change' and index==1:b['generation_settings']['grammar']='root ::= "changed"'
   (directory/'response_body.json').write_text(json.dumps(b));(directory/'content.txt').write_text(b['content']);(directory/'server_stderr.log').write_text('');return execution()
  def worker(req):
   score.append(req);case=next(c for c in CASES if c['item']==req['item'] and c['bins']==req['bins']);o=fake(case);o['worker_cpu_seconds']=0.01;return o
  count=[0]
  def verify(*a,**k):
   count[0]+=1
   if mode=='integrity' and count[0]==2:raise ValueError('synthetic changed input')
  class Budget:
   def __init__(self,p):self.calls=0
   def reserve(self,kind):
    self.calls+=1
    if mode=='budget' and self.calls==6:raise RuntimeError('synthetic budget stop')
   def score_mark(self):return None
   def score_charge(self,m):pass
   def terminal(self):return {'within_charged_budget':True,'scope':'synthetic mock, not measured'}
  oldsave=m.save
  def save(path,obj):
   if mode=='persistence' and pathlib.Path(path).name=='observation.json':raise OSError('synthetic persistence fault')
   return oldsave(path,obj)
  with patch.object(m,'ROOT',p),patch.object(m,'verify',verify),patch.object(m,'Budget',Budget),patch.object(m,'save',save),patch.object(m.resource,'setrlimit'),patch.dict(sys.modules,{'backend':types.SimpleNamespace(run_once=backend),'runtime':types.SimpleNamespace(request=worker)}),contextlib.redirect_stdout(io.StringIO()):
   r=m.execute(PLAN,'f'*64,{'run_id':'mock','scope':'p3_compact_dag_interface3_once'})
  td.cleanup();return r,calls,score
 def test_all_3_by_3(self):
  r,c,s=self.run_fake();self.assertEqual(r['state'],'completed');self.assertEqual(len(c),3);self.assertEqual(len(s),9);self.assertEqual(len(r['ledger']),9);self.assertFalse(r['any_design_gate_met']);self.assertTrue(all(x['representation_matches_example'] for x in r['requests']));self.assertFalse(r['requests'][0]['minimal_design_gate_met'])
 def test_caps_all_retained(self):
  r,c,s=self.run_fake('caps');self.assertEqual(len(c),3);self.assertFalse(s);self.assertTrue(all(x['status']=='generation_failed' for x in r['requests']));self.assertFalse(r['any_design_gate_met'])
 def test_grammar_stop(self):
  r,c,s=self.run_fake('grammar_change');self.assertEqual(r['state'],'incomplete');self.assertEqual(len(c),2);self.assertEqual(len(s),3);self.assertEqual(r['requests'][2]['status'],'not_run')
 def test_zero_dispatch_integrity(self):
  r,c,s=self.run_fake('integrity');self.assertFalse(c);self.assertFalse(s);self.assertEqual(r['formal_posts_observed'],0);self.assertEqual(r['unknown_launch_states'],0)
 def test_midbudget_preserves(self):
  r,c,s=self.run_fake('budget');self.assertEqual(r['state'],'incomplete');self.assertEqual(len(c),2);self.assertEqual(len(s),3);self.assertFalse(r['any_design_gate_met'])
 def test_returned_observation_persistence(self):
  r,c,s=self.run_fake('persistence');self.assertEqual(len(c),1);self.assertEqual(len(s),1);self.assertEqual(r['score_dispatches'],1);self.assertEqual(r['unknown_launch_states'],0);self.assertEqual(r['ledger'][0]['status'],'infrastructure_failure')
if __name__=='__main__':unittest.main()
