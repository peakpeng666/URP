"""Fixed data-only selection and prompt assembly. No model or numerical execution."""
import hashlib,json,pathlib,sys
from fractions import Fraction
ROOT=pathlib.Path(__file__).resolve().parents[1]
EVALUATOR=ROOT.parent/'math_dag_v1';sys.path.insert(0,str(EVALUATOR/'src'))
from schema import validate_program,StructureError

def graph_identity(raw):
 p=validate_program(raw)
 constants=[[t,float(v).hex() if t=='f64' else v] for t,v in p.constants]
 data={'constants':constants,'nodes':p.nodes,'return_node':p.return_node}
 return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def fitness(case_results,expected_case_ids):
 if type(expected_case_ids) is not list or len(expected_case_ids)!=4 or len(set(expected_case_ids))!=4:raise ValueError('frozen design IDs')
 if [x.get('case_id') for x in case_results]!=expected_case_ids:raise ValueError('exact design case order/binding')
 if len(case_results)!=4 or any(x.get('status')!='completed_valid' for x in case_results):return None
 used=[];bounds=[]
 for x in case_results:
  if type(x.get('used_bins')) is not int or type(x.get('L1')) is not int or not 1<=x['L1']<=x['used_bins']<=128:raise ValueError('fitness evidence')
  used.append(x['used_bins']);bounds.append(x['L1'])
 total_used=sum(used);total_l1=sum(bounds)
 return {'excess_numerator':total_used-total_l1,'excess_denominator':total_l1,'sum_used_bins':total_used,'sum_L1':total_l1,'per_case_used':used,'per_case_L1':bounds}

def rank_key(record):
 f=record['fitness']
 return (Fraction(f['excess_numerator'],f['excess_denominator']),f['sum_used_bins'],record['source_order'])

def retain(records,n=2):
 eligible=[r for r in records if r.get('fitness') is not None]
 # Representation duplicates cannot occupy two parent positions. All original
 # request records/results still exist; this is retention, not denominator removal.
 earliest={}
 for r in sorted(eligible,key=lambda x:x['source_order']):
  old=earliest.get(r['graph_identity'])
  if old is not None and (old['fitness']!=r['fitness'] or old.get('behavior_signature')!=r.get('behavior_signature')):raise ValueError('duplicate deterministic result conflict')
  earliest.setdefault(r['graph_identity'],r)
 return sorted(earliest.values(),key=rank_key)[:n]

def parents(population,operator):
 if operator=='I1':return []
 if len(population)!=2 or len({r['graph_identity'] for r in population})!=2:raise ValueError('insufficient distinct eligible parents')
 p=sorted(population,key=rank_key)
 if operator in {'E1','E2'}:return p
 if operator in {'M1','M3'}:return [p[0]]
 if operator=='M2':return [p[1]]
 if operator=='I1':return []
 raise ValueError('unknown frozen operator')

def build_prompt(operator,parent_records):
 if operator not in {'I1','E1','E2','M1','M2','M3'}:raise ValueError('operator')
 expected=0 if operator=='I1' else 2 if operator in {'E1','E2'} else 1
 if len(parent_records)!=expected:raise ValueError('parent arity')
 text=(ROOT/'prompts/common.txt').read_text()+'\n'+(ROOT/'prompts'/(operator+'.txt')).read_text()
 for index,record in enumerate(parent_records):
  # Reserialization is only a deterministic presentation of an already admitted
  # parent. Its original model content/bytes are preserved and never repaired.
  raw=record['program_json'].encode();validate_program(raw)
  compact=json.dumps(json.loads(raw),separators=(',',':'),ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e')
  text+='\nParent '+str(index)+', exact design statistics '+json.dumps(record['fitness'],separators=(',',':'))+':\n'+compact+'\n'
 if len(text.encode())>32768:raise ValueError('prompt byte limit')
 return text

def initialize_ledger(plan,case_ids):
 rows=[]
 for slot in plan['slots']:
  for case in case_ids:
   rows.append({'slot_id':slot['slot_id'],'case_id':case['id'],'split':case['split'],'status':'not_run','reason':'awaiting_generation' if case['split']=='design' else 'not_selected_predeclared'})
 return rows

def commitment(evolution,control):
 if len(evolution)!=2 or len(control)!=2:raise ValueError('missing population')
 winners={'evolution':sorted(evolution,key=rank_key)[0],'control':sorted(control,key=rank_key)[0]}
 out={arm:{k:r[k] for k in ['source_id','source_order','graph_identity','raw_sha256','fitness','origin']} for arm,r in winners.items()}
 raw=json.dumps(out,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
 return out,hashlib.sha256(raw).hexdigest()

def structural_changes(parent_raw,child_raw):
 a=validate_program(parent_raw);b=validate_program(child_raw)
 types_same=[t for t,v in a.constants]==[t for t,v in b.constants]
 values_changed=graph_identity(parent_raw)!=graph_identity(child_raw) and a.nodes==b.nodes and a.return_node==b.return_node and types_same
 return {'same_graph_identity':graph_identity(parent_raw)==graph_identity(child_raw),'parent_nodes':len(a.nodes),'child_nodes':len(b.nodes),'nodes_changed':a.nodes!=b.nodes,'return_node_changed':a.return_node!=b.return_node,'constant_types_same':types_same,'constant_values_changed':[[t,float(v).hex() if t=='f64' else v] for t,v in a.constants]!=[[t,float(v).hex() if t=='f64' else v] for t,v in b.constants],'parameter_only_observed':values_changed,'shorter_node_count_observed':len(b.nodes)<len(a.nodes),'semantic_equivalence_proven':False}

def behavior_signature(case_results):
 if len(case_results)!=4 or any(x.get('status')!='completed_valid' for x in case_results):return None
 records=[]
 for x in case_results:
  if type(x.get('case_id')) is not str or type(x.get('assignment')) is not list or len(x['assignment'])!=128 or any(type(v) is not int or not 0<=v<128 for v in x['assignment']):raise ValueError('behavior evidence')
  records.append([x['case_id'],x['assignment']])
 return hashlib.sha256(json.dumps(records,separators=(',',':')).encode()).hexdigest()
