from collections import Counter
import hashlib,json
from pathlib import Path
from types import SimpleNamespace
import unittest
from fresh_initialization_replication_v1.experiment import replay_plan,run

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).parent
CONFIG=json.loads((HERE/'protocol.json').read_text())


class ReplicationTests(unittest.TestCase):
    def cases(self):
        ins=[SimpleNamespace(instance_id=f'unit-{i}',family='uniform' if i<10 else 'clustered') for i in range(20)]
        calls=[{'instance_id':i.instance_id,'seed':s,'profile':p,'algorithm':m} for i in ins for s in CONFIG['solver_seeds'] for p in CONFIG['profiles'] for m in CONFIG['algorithms']]
        return ins,calls

    def test_primary_scope(self):
        ins,calls=self.cases()
        self.assertEqual(len(calls),600)
        self.assertEqual(Counter((c['algorithm'],c['profile']) for c in calls),Counter({(m,p):100 for m in CONFIG['algorithms'] for p in CONFIG['profiles']}))

    def test_balanced_outcome_independent_replay_selection(self):
        ins,calls=self.cases();plan=replay_plan(calls,ins,CONFIG)
        self.assertEqual(len(plan['replay_call_indices']),120)
        self.assertEqual(len(set(plan['replay_call_indices'])),120)
        self.assertEqual(Counter(plan['selected_seed_by_instance'].values()),Counter({s:4 for s in CONFIG['solver_seeds']}))
        chosen=[calls[i] for i in plan['replay_call_indices']]
        self.assertEqual(Counter((c['algorithm'],c['profile']) for c in chosen),Counter({(m,p):20 for m in CONFIG['algorithms'] for p in CONFIG['profiles']}))
        for c in calls:c['fake_outcome']='failure'
        self.assertEqual(replay_plan(calls,ins,CONFIG),plan)

    def test_diagnostics_are_eight_predeclared_fixed_work_calls(self):
        ins,calls=self.cases();ds=replay_plan(calls,ins,CONFIG)['fixed_iteration_diagnostics']
        self.assertEqual(len(ds),8)
        self.assertEqual({d['instance_id'] for d in ds},{'unit-0','unit-10'})
        self.assertTrue(all(d['iterations']==100 and d['seed']==11 and d['cpu_budget_seconds']==5 and d['wall_budget_seconds']==10 for d in ds))
        self.assertEqual(Counter((d['instance_id'],d['algorithm']) for d in ds),Counter({(i,m):2 for i in ('unit-0','unit-10') for m in ('pyvrp_ils_random','pyvrp_ils_savings_warm')}))

    def test_actual_accepted_runtime_and_adapter_unchanged(self):
        self.assertEqual(run.__module__,'initialization_ablation_v1.runtime')
        freeze=json.loads((ROOT/'initialization_ablation_v1/runs/dev_20261004_01/freeze.json').read_text())
        for name in ('runtime.py','adapter.py'):
            rel='initialization_ablation_v1/'+name
            self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),freeze['source_hashes'][rel])

    def test_all_search_and_budget_parameters_match_accepted_study(self):
        prior=json.loads((ROOT/'initialization_ablation_v1/protocol.json').read_text())
        for k in ('profiles','common_cpu_return_margin_seconds','pyvrp_cpu_return_margin_seconds','pyvrp_iterations','move_evaluation_limit','move_improvement_epsilon','multistart_count'):
            self.assertEqual(CONFIG[k],prior[k])

    def test_fresh_seed_namespace_and_task_scope(self):
        seeds=set(range(CONFIG['generation_seed_base'],CONFIG['generation_seed_base']+20))
        self.assertEqual(seeds,set(range(2026100800,2026100820)))
        self.assertFalse(seeds.intersection(range(2026101400,2026101500)))
        for manifest in (ROOT/'data/dev/manifest.json',ROOT/'scale_budget_v1/data/dev/manifest.json'):
            old=json.loads(manifest.read_text())
            self.assertFalse(seeds.intersection({r['generation_seed'] for r in old['instances']}))
        self.assertEqual(CONFIG['customer_counts'],[200]);self.assertEqual(CONFIG['instances_per_cell'],10)
        self.assertEqual(CONFIG['solver_seeds'],[11,29,47,71,97])


if __name__=='__main__':unittest.main(verbosity=2)
