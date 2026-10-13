import ast,itertools,json,pathlib,pickle,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from baselines import pack,choose,feasible_indices
from extract_data import decode_numeric_pickle,literal,embedded_data,validate_lists
class Baselines(unittest.TestCase):
 def test_all_feasible(self):
  self.assertEqual(feasible_indices(3,[1,4,10,10]),[1,2,3]);self.assertEqual(choose(3,[1,4,10,10],'FF'),(1,3));self.assertEqual(choose(3,[1,4,10,10],'BF'),(1,3))
 def test_stable_ties(self):self.assertEqual(choose(3,[5,5,10],'BF'),(0,3))
 def test_different_policies(self):
  self.assertEqual(pack([6,5,4,5],10,'FF')['assignment'],[0,1,0,1])
  self.assertEqual(pack([4,8,1],10,'BF')['assignment'],[0,1,1]);self.assertEqual(pack([4,8,1],10,'FF')['assignment'],[0,1,0])
 def test_exact_empty(self):
  self.assertEqual(pack([10,10],10,'BF')['residuals'],[0,0]);self.assertEqual(pack([],10,'FF')['used_bins'],0)
 def test_rejections(self):
  for x,c in [([True],10),([1.0],10),([0],10),([11],10),([1],True),((1,),10)]:
   with self.assertRaises(ValueError):pack(x,c,'FF')
  with self.assertRaises(ValueError):pack([1],10,'EOH')
 def test_score_equivalence_exhaustive(self):
  for residuals in itertools.product(range(5),repeat=4):
   for item in range(1,5):
    ix=feasible_indices(item,residuals)
    if not ix:continue
    for method in ['FF','BF']:
     scores=[-j if method=='FF' else -(residuals[k]-item) for j,k in enumerate(ix)]
     expect=ix[scores.index(max(scores))]
     self.assertEqual(choose(item,residuals,method)[0],expect)
class Data(unittest.TestCase):
 def test_primitive_decode(self):
  # pickle.dumps produces hand-written test data only; no unpickling call exists.
  data={1000:[[1,2],[3,4]]};raw=pickle.dumps(data,protocol=4)
  self.assertEqual(decode_numeric_pickle(raw)[0],data)
 def test_reject_objects_aliases_trailing(self):
  for raw in [b'cos\nsystem\n.',pickle.dumps({'x':1},protocol=4),pickle.dumps([None],protocol=4),pickle.dumps([True],protocol=4),pickle.dumps({1:[1]},protocol=4)+b'x']:
   with self.assertRaises((ValueError,IndexError)):decode_numeric_pickle(raw)
  x=[]
  with self.assertRaises(ValueError):decode_numeric_pickle(pickle.dumps({1:[x,x]},protocol=4))
 def test_source_literal_reject(self):
  for src in ['f()','[x for x in y]','{"a": True}','{"a": 1.0}','{"a":1,"a":2}']:
   with self.assertRaises(ValueError):literal(ast.parse(src,mode='eval').body)
 def test_actual_input_schema_only(self):
  d=json.loads((ROOT/'data/numeric_datasets.json').read_text())['sets']
  for name,rows in d.items():validate_lists({len(rows[0]):rows},len(rows[0]))
  self.assertEqual(len(json.loads((ROOT/'prepared_plan.json').read_text())['slots']),60)
  for n in (1000,5000,10000):
   slots=[s for s in json.loads((ROOT/'prepared_plan.json').read_text())['slots'] if s['n']==n]
   self.assertEqual(len(slots),20)
   self.assertEqual(sum(s['capacity']==500 for s in slots),10)
 def test_no_old_overlap(self):
  d=json.loads((ROOT/'data/data_audit.json').read_text())
  for x in d['comparisons']:self.assertEqual(x['exact_matches'],[]);self.assertEqual(x['whole_shorter_sequence_prefix_matches'],[])
if __name__=='__main__':unittest.main()
