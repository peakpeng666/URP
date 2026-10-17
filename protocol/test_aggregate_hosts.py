import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from aggregate_hosts import aggregate_hosts
from test_aggregate import checked


class HostTests(unittest.TestCase):
    def setUp(self):
        self.plan = dict(case_ids=['c'], algorithms=['a', 'b'], seeds=[0, 3], budget_seconds=5,
                         cohort='test', protocol_sha256='p', case_manifest_sha256='m')
        self.cases = dict(cases=[dict(case_id='c', base_id='base', size_stratum='small',
                                     source_family='A', contract={'id': 'fixed'}, instance_sha256='c')])
        self.dist = dict(cases=[], family_metadata={'A': {'customer_distribution': 'R'}})
        self.assignment = {'canonical_plan_sha256': 'plan',
                           'machines': {'cloud': {'seeds': [0]}, 'ubuntu-local': {'seeds': [3]}}}
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def manifest(self, out, host='cloud', cohort='serial', **changes):
        env = out / 'environment.json'
        env.write_text('{"python": "test"}')
        manifest = dict(verification_status='VERIFIED', host_id=host, resource_cohort=cohort,
                        canonical_plan_sha256='plan', environment_manifest_path='environment.json',
                        environment_manifest_sha256=hashlib.sha256(env.read_bytes()).hexdigest())
        manifest.update(changes)
        (out / 'host_manifest.json').write_text(json.dumps(manifest))

    def put(self, algorithm='a', seed=0, host='cloud', cohort='serial', verified=True, **changes):
        out = self.root / f'{algorithm}-{seed}'
        out.mkdir()
        record = dict(schema='urp-cvrplib-result-v1', case_id='c', algorithm=algorithm, seed=seed,
                      budget_seconds=5, status='OK', feasible=True, cost=100, purpose='formal_baseline',
                      protocol_sha256='p', instance_sha256='c', case_manifest_sha256='m', plan_sha256='plan',
                      host_id=host, resource_cohort=cohort, cpu_seconds=2)
        record.update(changes)
        path = out / 'result.json'
        path.write_text(json.dumps(record))
        (out / 'evaluation.json').write_text(json.dumps(dict(
            result_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), candidate_check=checked(100),
            reference_check=checked(100), eligible_for_gap=True, gap_percent=0)))
        if verified:
            self.manifest(out, host, cohort)
        return out

    def aggregate(self):
        return aggregate_hosts(self.plan, self.cases, self.dist, self.root, self.assignment)

    def test_host_partition_no_cross_host_pairs_or_speed_pool(self):
        self.put()
        self.put('b')
        self.put(seed=3, host='ubuntu-local', cohort='two-lane')
        self.put('b', seed=3)
        rows, summary = self.aggregate()
        a = next(r for r in summary['groups']['overall']['pooled_quality_descriptive'] if r['algorithm'] == 'a')
        self.assertIsNone(a['cpu_seconds_mean_started'])
        self.assertEqual(sum(p['common_feasible_gap_rows'] for p in summary['pairwise_by_host_resource']), 1)
        self.assertEqual(summary['pairwise_by_host_resource'][0]['excluded_cross_host_or_unknown_pairs_for_algorithm_pair'], 1)
        self.assertEqual(sum(r['host_verified'] for r in rows), 4)

    def test_declaration_only_cannot_claim_verified_timing_or_pairs(self):
        self.put(verified=False)
        self.put('b', verified=False)
        rows, summary = self.aggregate()
        self.assertFalse(any(r['host_verified'] for r in rows))
        self.assertTrue(all(r['host_id'] == 'unknown' for r in rows if r['started']))
        self.assertTrue(all(r['declared_host_id'] == 'cloud' for r in rows if r['started']))
        self.assertTrue(all(r['cpu_seconds_mean_started'] is None for r in summary['groups']['overall']['pooled_quality_descriptive']))
        self.assertEqual(summary['pairwise_by_host_resource'][0]['common_feasible_gap_rows'], 0)

    def test_conflicting_resource_and_host_declarations_rejected(self):
        out = self.put()
        self.manifest(out, cohort='different')
        self.put('b', machine_id='another-machine')
        rows, _ = self.aggregate()
        self.assertFalse(any(r['host_verified'] for r in rows))
        self.assertEqual({r['host_provenance_error'] for r in rows if r['started']},
                         {'RESOURCE_COHORT_DECLARATION_CONFLICT', 'HOST_DECLARATION_CONFLICT'})

    def test_nearer_unverified_manifest_blocks_parent_inheritance(self):
        self.manifest(self.root)
        out = self.put(verified=False)
        (out / 'host_manifest.json').write_text('{"verification_status": "TEMPLATE"}')
        rows, _ = self.aggregate()
        row = next(r for r in rows if r['started'])
        self.assertFalse(row['host_verified'])
        self.assertEqual(row['host_provenance_error'], 'HOST_MANIFEST_NOT_VERIFIED')

    def test_missing_or_mismatched_environment_rejected(self):
        out = self.put()
        self.manifest(out, environment_manifest_sha256='wrong')
        rows, _ = self.aggregate()
        row = next(r for r in rows if r['started'])
        self.assertFalse(row['host_verified'])
        self.assertEqual(row['host_provenance_error'], 'HOST_ENVIRONMENT_HASH_MISMATCH')

    def test_wrong_plan_manifest_rejected(self):
        out = self.put()
        self.manifest(out, canonical_plan_sha256='another-plan')
        rows, _ = self.aggregate()
        self.assertEqual(next(r for r in rows if r['started'])['host_provenance_error'], 'HOST_PLAN_HASH_MISMATCH')

    def test_duplicate_seed_ownership_rejected(self):
        self.assignment['machines']['ubuntu-local']['seeds'].append(0)
        with self.assertRaisesRegex(ValueError, 'seed ownership'):
            self.aggregate()


if __name__ == '__main__':
    unittest.main()
