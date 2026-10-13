"""Pure stdlib fake observations and handwritten data; no worker/model process."""
import copy,hashlib,json,pathlib,struct,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from measurement import admit,check,identity
RAW=(ROOT/'data/fixed_target.json').read_bytes(); TARGET=json.loads(RAW);CASES=json.loads((ROOT/'data/manual_cases.json').read_text())['cases']
def fake(case=CASES[0]):
 p,_=admit(RAW);scores=case['fixed_target_scores'];n=len(scores)
 trace=[{'type':t,'dtype':{'vi64':'int64','vf64':'float64'}[t],'shape':[n],'sha256':'0'*64,'nan_count':0,'positive_infinity_count':0,'negative_infinity_count':0} for t in p.types]
 b={'pid':7,'limits':{'RLIMIT_AS':[2147483648]*2,'RLIMIT_CPU':[20]*2,'RLIMIT_FSIZE':[0]*2,'RLIMIT_NOFILE':[32]*2},'program_sha256':p.raw_sha256,'canonical_program_sha256':p.canonical_sha256,'phase':'evaluate','status':'completed_finite','error':None,'warnings':{'events':[],'kinds':[],'complete':True,'incomplete_reason':None},'work_units':n*4,'result':{'dtype':'float64','shape':[n],'scores':scores,'scores_sha256':hashlib.sha256(struct.pack('='+str(n)+'d',*scores)).hexdigest(),'first_argmax':case['fixed_target_index'],'node_trace':trace}}
 return {'pid':7,'returncode':0,'termination':None,'error':None,'reaped':True,'cpu_evidence_complete':True,'result':b}
class Tests(unittest.TestCase):
 def test_target_types(self):self.assertEqual(list(admit(RAW)[0].types),['vi64','vi64','vi64','vf64'])
 def test_three_expected_vectors(self):
  for c in CASES:
   expected=[-float((v-c['item']-20)**2) for v in c['bins']]
   self.assertEqual(c['fixed_target_scores'],expected)
   self.assertEqual(c['ff_index'],0);self.assertEqual(c['bf_index'],min(range(len(c['bins'])),key=c['bins'].__getitem__))
   self.assertEqual(check(RAW,c,fake(c))['first_argmax'],c['fixed_target_index'])
 def test_realized_difference(self):self.assertTrue(check(RAW,CASES[0],fake())['differs_from_ff_and_bf'])
 def test_matching_behavior_retained(self):self.assertFalse(check(RAW,CASES[2],fake(CASES[2]))['differs_from_ff_and_bf'])
 def test_compact_bounds(self):
  for field,value in [('description','x'*65),('constants',TARGET['constants']*2),('nodes',TARGET['nodes']+[TARGET['nodes'][-1]])]:
   d=copy.deepcopy(TARGET);d[field]=value
   with self.assertRaises(ValueError):admit(json.dumps(d).encode())
 def test_no_scalar_gt(self):
  d=copy.deepcopy(TARGET);d['nodes'][0]=['gt','item','c0']
  with self.assertRaises(ValueError):admit(json.dumps(d).encode())
 def test_undefined_constants(self):
  d=copy.deepcopy(TARGET);d['nodes'][0]=['sub','bins','c2']
  with self.assertRaises(ValueError):admit(json.dumps(d).encode())
 def test_no_forward_ref(self):
  d=copy.deepcopy(TARGET);d['nodes'][0]=['sub','bins',0]
  with self.assertRaises(ValueError):admit(json.dumps(d).encode())
 def test_bad_transport(self):
  for key,value in [('returncode',1),('termination','wall_timeout'),('error','oops'),('reaped',False),('cpu_evidence_complete',False),('pid',8)]:
   o=fake();o[key]=value
   with self.assertRaises(ValueError):check(RAW,CASES[0],o)
 def test_source_phase_limit_binding(self):
  for key,value in [('phase','pack'),('program_sha256','x'),('canonical_program_sha256','x'),('limits',{}),('pid',8)]:
   o=fake();o['result'][key]=value
   with self.assertRaises(ValueError):check(RAW,CASES[0],o)
 def test_infrastructure_not_numeric(self):
  for status in ['structural_rejected','input_rejected','infrastructure_failure','unexpected']:
   o=fake();o['result']['status']=status
   with self.assertRaises(ValueError):check(RAW,CASES[0],o)
 def test_unresolved_stays_distinct(self):
  for status in ['numeric_invalid','resource_unresolved','diagnostic_unresolved']:
   o=fake();o['result'].update(status=status,result=None,error={'type':'test','message':'fixed'})
   self.assertEqual(check(RAW,CASES[0],o)['status'],status)
 def test_wrong_score_types(self):
  for v in [0,True,float('nan'),float('inf')]:
   o=fake();o['result']['result']['scores']=list(o['result']['result']['scores']);o['result']['result']['scores'][0]=v
   with self.assertRaises(ValueError):check(RAW,CASES[0],o)
 def test_result_shapes(self):
  for key,value in [('shape',[2]),('dtype','int64'),('scores_sha256','0'*64),('first_argmax',True),('first_argmax',0),('node_trace',[])]:
   o=fake();o['result']['result'][key]=value
   with self.assertRaises(ValueError):check(RAW,CASES[0],o)
 def test_tie_is_first(self):
  o=fake(CASES[1]);o['result']['result']['first_argmax']=3
  with self.assertRaises(ValueError):check(RAW,CASES[1],o)
 def test_work_count(self):
  o=fake();o['result']['work_units']=13
  with self.assertRaises(ValueError):check(RAW,CASES[0],o)
 def test_warning_shape(self):
  for w in [{},{'events':[],'kinds':[],'complete':True,'incomplete_reason':'oops'},{'events':[[1,0,0]],'kinds':[],'complete':True,'incomplete_reason':None}]:
   o=fake();o['result']['warnings']=w
   with self.assertRaises(ValueError):check(RAW,CASES[0],o)
 def test_description_not_identity(self):
  d=copy.deepcopy(TARGET);d['description']='Same rule.'
  self.assertEqual(identity(admit(RAW)[0]),identity(admit(json.dumps(d).encode())[0]))
 def test_signed_zero_identity(self):
  d=copy.deepcopy(TARGET);d['constants'][1]['value']=0.0;p=identity(admit(json.dumps(d).encode())[0]);d['constants'][1]['value']=-0.0
  self.assertNotEqual(p,identity(admit(json.dumps(d).encode())[0]))
if __name__=='__main__':unittest.main()
