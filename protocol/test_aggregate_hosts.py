import hashlib,json,tempfile,unittest
from pathlib import Path
from aggregate_hosts import aggregate_hosts
class HostTests(unittest.TestCase):
 def test_host_partition_no_cross_host_pairs_or_speed_pool(self):
  plan=dict(case_ids=['c'],algorithms=['a','b'],seeds=[0,3],budget_seconds=5,cohort='test',protocol_sha256='p',case_manifest_sha256='m')
  cases=dict(cases=[dict(case_id='c',base_id='base',size_stratum='small',source_family='A',contract={'id':'fixed'},instance_sha256='c')]);dist=dict(cases=[],family_metadata={'A':{'customer_distribution':'R'}});assignment={'machines':{'cloud':{'seeds':[0]},'ubuntu-local':{'seeds':[3]}}}
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for a,s,host,cohort in [('a',0,'cloud','serial'),('b',0,'cloud','serial'),('a',3,'ubuntu-local','two-lane'),('b',3,'cloud','serial')]:
    out=root/f'{a}-{s}';out.mkdir();r=dict(case_id='c',algorithm=a,seed=s,budget_seconds=5,status='OK',feasible=True,purpose='formal_baseline',protocol_sha256='p',instance_sha256='c',case_manifest_sha256='m',host_id=host,resource_cohort=cohort,cpu_seconds=2);f=out/'result.json';f.write_text(json.dumps(r));(out/'evaluation.json').write_text(json.dumps(dict(result_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),candidate_check={'valid':True,'reported_cost_checked':True,'cost':100},eligible_for_gap=True,gap_percent=0)))
   rows,x=aggregate_hosts(plan,cases,dist,root,assignment);a=next(r for r in x['groups']['overall']['pooled_quality_descriptive'] if r['algorithm']=='a');self.assertIsNone(a['cpu_seconds_mean_started']);self.assertEqual(sum(p['common_feasible_gap_rows'] for p in x['pairwise_by_host_resource']),1);self.assertEqual(x['pairwise_by_host_resource'][0]['excluded_cross_host_or_unknown_pairs_for_algorithm_pair'],1)
if __name__=='__main__':unittest.main()
