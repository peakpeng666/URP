"""Re-audit the archived main CVRP baseline without invoking any solver.

Only a new output file and temporary extraction directory are written. This
checks archive identity, every terminal witness, all reference solutions, the
full plan denominator, and the evidence needed for host-stratified statistics.
"""
import argparse
from collections import Counter
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile

from audit_results import audit
from validate import check, read_instance, read_solution, sha

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'protocol'))
from aggregate_hosts import aggregate_hosts


def extract_main_archives(source, destination):
    """Verify the published digests and extract regular files under new roots."""
    manifest = json.loads((source / 'manifest.json').read_text())
    evidence = []
    for entry in manifest['archives']:
        name = entry['file']
        if name == 'native-results.tar.xz':
            continue  # Separate vendor cohort, never part of the 4505 denominator.
        if Path(name).name != name or not name.endswith('.tar.xz'):
            raise ValueError('Invalid archive filename')
        archive = source / name
        if archive.stat().st_size != entry['bytes'] or sha(archive) != entry['sha256']:
            raise ValueError('Archive identity mismatch: ' + name)
        target_root = destination / name.removesuffix('.tar.xz')
        target_root.mkdir()
        files = results = 0
        with tarfile.open(archive, 'r:xz') as stream:
            for member in stream:
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('Unsafe archive member')
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError('Archive contains a non-regular file')
                target = target_root.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write(stream.extractfile(member).read())
                files += 1
                results += relative.name == 'result.json'
        evidence.append(dict(file=name, bytes=entry['bytes'], sha256=entry['sha256'],
                             verified=True, extracted_files=files, terminal_results=results))
    return evidence


def nearest(path, filename, boundary):
    for parent in path.parents:
        if parent != boundary and boundary not in parent.parents:
            break
        candidate = parent / filename
        if candidate.is_file():
            return candidate
    return None


def reference_audit(root, cases):
    references = {}
    errors = []
    for case in cases['cases']:
        raw = root / case['instance_path']
        reference = root / case['reference']['path']
        problem = read_instance(raw)
        routes, cost = read_solution(reference)
        limit = case['contract']['vehicle_limit'] or len(problem['demands']) - 1
        checked = check(problem, routes, cost, limit)
        if (sha(raw) != case['instance_sha256'] or sha(reference) != case['reference']['sha256']
                or not checked['valid'] or cost != case['reference']['cost']):
            errors.append(case['case_id'])
        else:
            references[case['case_id']] = cost
    return references, errors


def original_comparison(root, rows, summary):
    original_dir = root / 'experiments/baselines/cvrp/results'
    original = json.loads((original_dir / 'summary.json').read_text())
    with (original_dir / 'runs.csv').open() as stream:
        published_rows=list(csv.DictReader(stream))
    old_rows = {(r['case_id'], r['algorithm'], int(r['seed']), float(r['budget_seconds'])): r for r in published_rows}
    if len(old_rows)!=len(published_rows):raise ValueError('Duplicate keys in published result table')
    row_changes = []
    for row in rows:
        key = row['case_id'], row['algorithm'], row['seed'], row['budget_seconds']
        old = old_rows.get(key)
        if old is None:
            row_changes.append(list(key))
            continue
        old_cost = int(old['cost']) if old['cost'] else None
        old_gap = float(old['gap_percent']) if old['gap_percent'] else None
        if (old['feasible'] == 'True', old_cost, old_gap) != (row['feasible'], row['cost'], row['gap_percent']):
            row_changes.append(list(key))
    quality_fields = ('planned', 'started', 'not_started', 'feasible', 'failed_started',
                      'gap_rows', 'quality_case_count', 'quality_base_count',
                      'case_equal_gap_percent', 'base_equal_gap_percent')
    group_changes = []
    group_count = 0
    for axis, groups in summary['groups'].items():
        previous = {(r['algorithm'], r['group']): r for r in original['groups'][axis]['pooled_quality_descriptive']}
        for row in groups['pooled_quality_descriptive']:
            group_count += 1
            old = previous[(row['algorithm'], row['group'])]
            if any(row[k] != old[k] for k in quality_fields):
                group_changes.append([axis, row['algorithm'], row['group']])
    def pairs_by_cohort(value):
        counter = Counter()
        for row in value['pairwise_by_host_resource']:
            counter[row.get('resource_cohort') or 'unknown'] += row['common_feasible_gap_rows']
        return dict(counter)
    old_pairs = pairs_by_cohort(original)
    new_pairs = pairs_by_cohort(summary)
    return dict(original_summary_sha256=sha(original_dir / 'summary.json'),
                original_runs_csv_sha256=sha(original_dir / 'runs.csv'),
                compared_terminal_rows=len(rows), changed_quality_row_count=len(row_changes),
                changed_quality_row_examples=row_changes[:20], compared_pooled_groups=group_count,
                changed_pooled_quality_group_count=len(group_changes), changed_pooled_quality_groups=group_changes[:20],
                published_same_host_gap_pairs=sum(old_pairs.values()),
                archived_verified_same_host_gap_pairs=sum(new_pairs.values()),
                published_pairs_by_resource_cohort=old_pairs, verified_pairs_by_resource_cohort=new_pairs,
                published_overall_cpu_groups=sum(r['cpu_seconds_mean_started'] is not None for r in original['groups']['overall']['by_host_resource']),
                archived_verified_overall_cpu_groups=sum(r['cpu_seconds_mean_started'] is not None for r in summary['groups']['overall']['by_host_resource']))


def retry_audit(raw, records):
    evidence = []
    errors = []
    for path in sorted(raw.rglob('*adjudication*.json')):
        document = json.loads(path.read_text())
        if document.get('schema') != 'urp-cvrp-interrupted-claims-v1':
            continue
        for item in document['claimed_without_result']:
            candidates = list(raw.rglob(Path(item['claim']).name))
            claims = [p for p in candidates if all(json.loads(p.read_text()).get(k)==item[k]
                                                  for k in ('key','output','claimed_utc'))]
            claim_hashes={sha(c) for c in claims}
            retries = [(p, r) for p, r in records.items()
                       if r.get('retry_parent_claim_sha256') in claim_hashes]
            if len(claims) != 1 or len(retries) != 1:
                errors.append('claim/retry multiplicity: ' + Path(item['claim']).name)
                continue
            claim = claims[0]
            retry_path, retry = retries[0]
            manifest_path = nearest(retry_path, 'resource-manifest.json', raw)
            manifest = json.loads(manifest_path.read_text()) if manifest_path else {}
            declared = manifest.get('infrastructure_retries', {})
            policy_bound = (manifest_path is not None and sha(manifest_path) == retry.get('resource_manifest_sha256')
                            and any(v.get('claim_sha256') == sha(claim) for v in declared.values())
                            and bool(manifest.get('retry_selection_policy')))
            original_case = item['key']
            identity_bound = all(retry.get(k) == original_case.get(k) for k in
                                 ('instance_sha256', 'algorithm', 'seed', 'budget_seconds', 'contract', 'solver_source_sha256', 'plan_sha256'))
            # The original consumed claim has no terminal result; do not invent
            # its feasibility, elapsed time, or a score for best-of-retries.
            original_output = claim.parent.parent / Path(item['output']).name / 'result.json'
            no_original_result = not original_output.exists()
            if not policy_bound or not identity_bound or not no_original_result:
                errors.append('retry evidence mismatch: ' + retry['case_id'] + '/' + retry['algorithm'])
            evidence.append(dict(case_id=retry['case_id'], algorithm=retry['algorithm'], seed=retry['seed'],
                                 original_claim=str(claim.relative_to(raw)), original_claim_sha256=sha(claim),
                                 adjudication=str(path.relative_to(raw)), adjudication_sha256=sha(path),
                                 retry_result=str(retry_path.relative_to(raw)), retry_result_sha256=sha(retry_path),
                                 retry_resource_manifest_sha256=sha(manifest_path) if manifest_path else None,
                                 policy_bound_to_retry=policy_bound, same_planned_key=identity_bound,
                                 original_terminal_result_absent=no_original_result,
                                 retry_selection_policy=manifest.get('retry_selection_policy')))
    return evidence, errors


def review(root, raw, archive_evidence):
    plan_path = root / 'protocol/formal_plan.json'
    plan_digest=sha(plan_path)
    plan = json.loads(plan_path.read_text())
    cases_path = root / 'src/research/configs/cvrplib_cases.json'
    cases = json.loads(cases_path.read_text())
    assignment = json.loads((root / 'protocol/ownership_assignment_v3.json').read_text())
    if sha(cases_path) != plan['case_manifest_sha256'] or sha(root / plan['protocol_path']) != plan['protocol_sha256']:
        raise ValueError('Frozen protocol/case manifest identity mismatch')
    if assignment['canonical_plan_sha256'] != plan_digest:
        raise ValueError('Ownership assignment belongs to a different plan')
    checked = audit(root, raw, plan['planned_keys'])
    rows, summary = aggregate_hosts(plan, cases, json.loads((root / 'protocol/distribution_metadata.json').read_text()), raw, assignment)
    records = {Path(row['result_path']): json.loads(Path(row['result_path']).read_text()) for row in rows if row['started']}
    independent_by_file = {str(raw / row['file']): row['eligible'] for row in checked['rows']}
    feasibility_disagreements = [str(Path(row['result_path']).relative_to(raw)) for row in rows if row['started']
                                and row['feasible'] != independent_by_file[str(Path(row['result_path']))]]
    references, reference_errors = reference_audit(root, cases)
    gap_errors = []
    for row in rows:
        if row['gap_percent'] is not None:
            reference = references.get(row['case_id'])
            if reference is None or row['gap_percent'] != float(Fraction(100 * (row['cost'] - reference), reference)):
                gap_errors.append([row['case_id'], row['algorithm'], row['seed']])
    levels = Counter()
    cohorts = Counter()
    resource_errors = []
    resource_manifests={}
    for row in rows:
        if not row['started']:
            continue
        path = Path(row['result_path'])
        record = records[path]
        manifest_path = nearest(path, 'resource-manifest.json', raw)
        if row['host_verified']:
            level = 'verified_host_manifest_and_environment_hash'
        elif manifest_path is not None:
            if manifest_path not in resource_manifests:
                resource_manifests[manifest_path]=(json.loads(manifest_path.read_text()),sha(manifest_path))
            manifest,manifest_digest=resource_manifests[manifest_path]
            bound = (manifest.get('schema') == 'urp-local-resource-batch-v1' and manifest.get('status') == 'FROZEN'
                     and manifest_digest == record.get('resource_manifest_sha256')
                     and manifest.get('canonical_plan_sha256') == plan_digest
                     and manifest.get('solver_source_sha256') == plan['solver_source_sha256']
                     and manifest.get('machine_id') == record.get('machine_id')
                     and manifest.get('resource_batch_id') == record.get('resource_batch_id'))
            level = 'result_bound_resource_manifest_without_archived_host_verification' if bound else 'resource_manifest_mismatch'
            if not bound:
                resource_errors.append(str(path.relative_to(raw)))
        elif row['host_provenance_error'] == 'HOST_MANIFEST_NOT_VERIFIED':
            level = 'unverified_host_manifest_and_result_declarations'
        else:
            level = 'missing_or_conflicting_execution_provenance'
        levels[level] += 1
        cohorts[(row['seed'], row['host_id'] if row['host_verified'] else row['declared_host_id'],
                 row['resource_cohort'] if row['host_verified'] else row['declared_resource_cohort'], level)] += 1
    retries, retry_errors = retry_audit(raw, records)
    comparison = original_comparison(root, rows, summary)
    audit_sources = ['independent/audit_archives.py', 'independent/audit_results.py', 'independent/validate.py',
                     'protocol/aggregate.py', 'protocol/aggregate_hosts.py']
    return dict(schema='urp-cvrplib-archive-reaudit-v1', scope='Read-only main baseline re-audit; no solver runs; vendor120 excluded',
                plan_sha256=plan_digest, baseline_solver_source_sha256=plan['solver_source_sha256'],
                audit_source_sha256={name: sha(ROOT / name) for name in audit_sources}, archives=archive_evidence,
                denominator=dict(planned=plan['planned_keys'], terminal_results=checked['attempted'],
                                 not_started=checked['not_started'], extra_consumed_claims_without_terminal_result=len(retries),
                                 recorded_attempts_including_interrupted_claims=checked['attempted'] + len(retries),
                                 duplicate_terminal_keys=checked['duplicate_keys'], unexpected_terminal_results=summary['unexpected_results']),
                quality=dict(independently_eligible=checked['eligible'], failed_terminal_results=checked['attempted'] - checked['eligible'],
                             aggregation_feasible=sum(row['feasible'] for row in rows),
                             feasibility_disagreement_count=len(feasibility_disagreements), feasibility_disagreement_examples=feasibility_disagreements[:20],
                             independent_audit_error_count=len(checked['audit_errors']), independent_audit_error_examples=checked['audit_errors'][:20],
                             status_counts=checked['status_counts'], checked_reference_cases=len(references), reference_errors=reference_errors,
                             independently_recomputed_gap_rows=sum(r['gap_percent'] is not None for r in rows), gap_error_count=len(gap_errors),
                             gap_error_examples=gap_errors[:20], negative_reference_gaps=sum(r['reference_review_required'] for r in rows),
                             algorithm_results=[{k: r[k] for k in ('algorithm', 'planned', 'feasible', 'failed_started', 'gap_rows', 'case_equal_gap_percent', 'base_equal_gap_percent')}
                                                for r in summary['groups']['overall']['pooled_quality_descriptive']]),
                provenance=dict(level_counts=dict(levels), resource_binding_error_count=len(resource_errors),
                                resource_binding_error_examples=resource_errors[:20],
                                cohorts=[dict(seed=s, recorded_host_id=h, recorded_resource_cohort=c, evidence_level=l, terminal_results=n)
                                         for (s, h, c, l), n in sorted(cohorts.items())]),
                comparison=comparison, interrupted_claims_and_retries=retries, retry_evidence_errors=retry_errors,
                conclusions=[
                    'Candidate feasibility and reference gaps are distinct from verification of host/resource provenance.',
                    'Pooled quality remains descriptive heterogeneous-hardware evidence; seeds are confounded with machines.',
                    'Only archived VERIFIED host manifests with matching plan and environment hashes qualify for verified CPU and same-host pairing.',
                    'Result-bound local resource manifests retain useful evidence but do not replace absent archived host/environment verification wrappers.',
                    'The four initial consumed claims have no recoverable terminal witness; count attempts without inventing their scores or times.',
                    'This audit adds a correction alongside immutable historical reports and never changes the original archive bytes.'
                ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True, help='New compact audit JSON; existing files are not overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    with tempfile.TemporaryDirectory(prefix='urp-archive-audit-') as directory:
        raw = Path(directory)
        evidence = extract_main_archives(args.root / 'experiments/baselines/cvrp/raw', raw)
        report = review(args.root, raw, evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: report[k] for k in ('denominator', 'comparison')}, ensure_ascii=False))
    return int(bool(report['quality']['independent_audit_error_count'] or report['quality']['reference_errors']
                    or report['quality']['gap_error_count'] or report['quality']['feasibility_disagreement_count']
                    or report['provenance']['resource_binding_error_count'] or report['retry_evidence_errors']
                    or report['denominator']['duplicate_terminal_keys'] or report['denominator']['unexpected_terminal_results']))


if __name__ == '__main__':
    raise SystemExit(main())
