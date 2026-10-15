import hashlib,json,tempfile,unittest
from pathlib import Path
from aggregate import aggregate
class TestAggregate(unittest.TestCase):
 def test_denominators_and_pairs(self):
  plan=dict(case_ids=['c1','c2'],algorithms=['a','b'],seeds=[0,1],budget_seconds=5,cohort='test',protocol_sha256='p',case_manifest_sha256='m')
  cases=dict(cases=[dict(case_id=c,base_id='same_base',size_stratum='small',source_family='A',contract={'id':'fixed'},instance_sha256=c) for c in ['c1','c2']]);dist=dict(cases=[],family_metadata={'A':{'customer_distribution':'R'}})
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   def put(c,a,s,status,feasible,cost=100,gap=0,badhash=False):
    out=root/f'{c}-{a}-{s}';out.mkdir();r=dict(case_id=c,algorithm=a,seed=s,budget_seconds=5,status=status,feasible=feasible,purpose='formal_baseline',protocol_sha256='p',instance_sha256=c,case_manifest_sha256='m');f=out/'result.json';f.write_text(json.dumps(r));e=dict(result_sha256='bad' if badhash else hashlib.sha256(f.read_bytes()).hexdigest(),candidate_check=dict(valid=feasible,reported_cost_checked=feasible,cost=cost),eligible_for_gap=feasible,gap_percent=gap);(out/'evaluation.json').write_text(json.dumps(e))
   put('c1','a',0,'OK',True,gap=2);put('c1','b',0,'TIMEOUT_WITH_FEASIBLE_INCUMBENT',True,gap=4);put('c1','a',1,'TIMEOUT_NO_SOLUTION',False);put('c2','a',0,'OK',True,gap=8);put('c2','b',0,'OK',True,badhash=True)
   rows,summary=aggregate(plan,cases,dist,root)
   self.assertEqual(len(rows),8);a=next(x for x in summary['groups']['overall'] if x['algorithm']=='a');self.assertEqual((a['planned'],a['started'],a['feasible'],a['failed_started'],a['not_started']),(4,3,2,1,1));self.assertEqual(a['case_equal_gap_percent'],5);self.assertEqual(a['base_equal_gap_percent'],5);pair=summary['pairwise'][0];self.assertEqual(pair['common_feasible_gap_rows'],1);self.assertEqual(pair['case_equal_gap_difference_percentage_points'],-2);self.assertEqual(sum(x['status']=='CHECKER_HASH_MISMATCH' for x in rows),1)
if __name__=='__main__': unittest.main()
