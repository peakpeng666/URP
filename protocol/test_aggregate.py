import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from aggregate import aggregate


def checked(cost, valid=True):
    return dict(valid=valid, feasible=valid, reported_cost_checked=valid,
                reported_cost_matches=valid, cost=cost, errors=[] if valid else ['no solution'])


class TestAggregate(unittest.TestCase):
    def setUp(self):
        self.plan = dict(case_ids=['c1', 'c2'], algorithms=['a', 'b'], seeds=[0, 1],
                         budget_seconds=5, cohort='test', protocol_sha256='p', case_manifest_sha256='m')
        self.cases = dict(cases=[dict(case_id=c, base_id='same_base', size_stratum='small',
                                     source_family='A', contract={'id': 'fixed'}, instance_sha256=c)
                                for c in ['c1', 'c2']])
        self.dist = dict(cases=[], family_metadata={'A': {'customer_distribution': 'R'}})
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, c='c1', a='a', s=0, status='OK', feasible=True, gap=0,
            badhash=False, result_changes=None, evaluation_changes=None):
        out = self.root / f'{c}-{a}-{s}'
        out.mkdir()
        cost = 100 + gap if feasible else None
        record = dict(schema='urp-cvrplib-result-v1', case_id=c, algorithm=a, seed=s,
                      budget_seconds=5, status=status, feasible=feasible, cost=cost,
                      purpose='formal_baseline', protocol_sha256='p', instance_sha256=c,
                      case_manifest_sha256='m', cpu_seconds=2)
        record.update(result_changes or {})
        path = out / 'result.json'
        path.write_text(json.dumps(record))
        evaluation = dict(result_sha256='bad' if badhash else hashlib.sha256(path.read_bytes()).hexdigest(),
                          candidate_check=checked(cost, feasible), reference_check=checked(100),
                          eligible_for_gap=feasible, gap_percent=gap)
        evaluation.update(evaluation_changes or {})
        (out / 'evaluation.json').write_text(json.dumps(evaluation))
        return out

    def run_aggregate(self, plan=None):
        return aggregate(plan or self.plan, self.cases, self.dist, self.root)

    def test_denominators_and_pairs(self):
        self.put(gap=2)
        self.put(a='b', status='TIMEOUT_WITH_FEASIBLE_INCUMBENT', gap=4)
        self.put(s=1, status='TIMEOUT_NO_SOLUTION', feasible=False)
        self.put(c='c2', gap=8)
        self.put(c='c2', a='b', badhash=True)
        rows, summary = self.run_aggregate()
        self.assertEqual(len(rows), 8)
        a = next(x for x in summary['groups']['overall'] if x['algorithm'] == 'a')
        self.assertEqual(tuple(a[k] for k in ('planned', 'started', 'feasible', 'failed_started', 'not_started')),
                         (4, 3, 2, 1, 1))
        self.assertEqual(a['case_equal_gap_percent'], 5)
        self.assertEqual(a['base_equal_gap_percent'], 5)
        pair = summary['pairwise'][0]
        self.assertEqual(pair['common_feasible_gap_rows'], 1)
        self.assertEqual(pair['case_equal_gap_difference_percentage_points'], -2)
        self.assertEqual(sum(x['status'] == 'CHECKER_HASH_MISMATCH' for x in rows), 1)

    def test_duplicate_axes_denominator_and_schedule_rejected(self):
        for change in ({'seeds': [0, 0]}, {'case_ids': ['c1', 'c1']},
                       {'seeds': [False, 1]}, {'planned_keys': 9}, {'schedule': []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_aggregate(dict(self.plan, **change))

    def test_duplicate_attempt_never_becomes_best_of_retries(self):
        original = self.put()
        retry = self.root / 'retry'
        retry.mkdir()
        (retry / 'result.json').write_bytes((original / 'result.json').read_bytes())
        with self.assertRaisesRegex(ValueError, 'Duplicate attempt key'):
            self.run_aggregate()

    def test_truthy_flags_and_noninteger_cost_do_not_pass(self):
        self.put(result_changes={'feasible': 'true'})
        self.put(a='b', evaluation_changes={'candidate_check': dict(checked(100), valid=1)})
        self.put(s=1, evaluation_changes={'candidate_check': checked(100.0)})
        self.put(a='b', s=1, evaluation_changes={'candidate_check': checked(float('nan'))})
        rows, _ = self.run_aggregate()
        self.assertEqual(sum(r['started'] for r in rows), 4)
        self.assertFalse(any(r['feasible'] for r in rows))

    def test_reference_and_gap_corruption_retains_feasibility_without_quality(self):
        self.put(evaluation_changes={'reference_check': checked(100, False)})
        self.put(a='b', evaluation_changes={'gap_percent': float('nan')})
        self.put(s=1, evaluation_changes={'gap_percent': 900})
        rows, _ = self.run_aggregate()
        self.assertEqual(sum(r['feasible'] for r in rows), 3)
        self.assertFalse(any(r['gap_percent'] is not None for r in rows))
        self.assertEqual(sum(r['gap_status'] == 'GAP_MISMATCH' for r in rows), 2)

    def test_invalid_measurement_and_checker_kept_in_denominator(self):
        self.put(result_changes={'cpu_seconds': float('nan')})
        out = self.put(a='b')
        (out / 'evaluation.json').write_text('{')
        rows, summary = self.run_aggregate()
        self.assertEqual(sum(r['started'] for r in rows), 2)
        a = next(r for r in rows if r['started'] and r['algorithm'] == 'a')
        self.assertTrue(a['feasible'])
        self.assertIsNone(a['cpu_seconds'])
        self.assertEqual(a['measurement_errors'], ['invalid cpu_seconds'])
        self.assertEqual(sum(r['status'] == 'CHECKER_INVALID' for r in rows), 1)
        json.dumps(summary, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
