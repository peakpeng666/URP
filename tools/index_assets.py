#!/usr/bin/env python3
"""Index tracked binary assets and third-party license evidence at one commit."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LICENSE_NAMES = ('license', 'licence', 'copying', 'notice', 'copyright')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def tree(ref, *paths):
    entries = []
    for row in git('ls-tree', '-r', '-z', ref, *paths).split(b'\0'):
        if row:
            meta, path = row.decode().split('\t', 1)
            mode, kind, oid = meta.split()
            entries.append({'path': path, 'mode': mode, 'kind': kind, 'oid': oid})
    return entries


def asset_kind(path):
    lower = path.lower()
    if lower.endswith('.pdf'):
        return 'textbook' if path.startswith('literature/教材/') else 'paper' if path.startswith('papers/') else 'document'
    if lower.endswith(('.zip', '.tar.gz', '.tgz', '.tar.zst', '.7z', '.rar')):
        return 'experiment-archive' if path.startswith('experiments/') else 'third-party-archive' if path.startswith('src/repos/') else 'archive'
    if lower.endswith(('.sqlite', '.sqlite3', '.db')):
        return 'database'
    if path.startswith('data/cifar-training/') or lower.endswith(('.pt', '.pth', '.npz', '.npy', '.whl')):
        return 'dataset-or-model'
    return None


def license_label(content):
    lower = content.lower()
    if 'gnu affero general public license' in lower:
        return 'AGPL: review version and scope'
    if 'gnu lesser general public license' in lower:
        return 'LGPL: review version and scope'
    if 'gnu general public license' in lower:
        return 'GPL: review version and scope'
    if 'attribution-noncommercial 4.0 international' in lower:
        return 'CC-BY-NC-4.0'
    if 'polyform noncommercial license 1.0.0' in lower:
        return 'PolyForm-Noncommercial-1.0.0'
    if any(term in lower for term in ('non-commercial', 'noncommercial', 'non commercial', 'research purposes only')):
        return 'restricted-terms: review text'
    if 'permission is hereby granted, free of charge' in lower:
        return 'MIT-style'
    if 'apache license' in lower and 'version 2.0' in lower:
        return 'Apache-2.0'
    if 'redistribution and use in source and binary forms' in lower:
        return 'BSD-style: review clauses'
    return 'custom-or-unidentified: review text'


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def verified_copies(path):
    if not path.is_file():
        return {}, []
    records = json.loads(path.read_text())['copies']
    verified = {}
    for record in records:
        if record['state'] != 'restore-verified':
            continue
        if (not record.get('asset_path') or not record.get('url', '').startswith('https://')
                or not re.fullmatch(r'[0-9a-f]{40}', record.get('git_blob_sha1', ''))
                or not re.fullmatch(r'[0-9a-f]{64}', record.get('sha256', ''))
                or not record.get('restore_evidence')):
            raise ValueError('Verified copies require an asset path, URL, content hashes and restore evidence')
        if record['asset_path'] in verified:
            raise ValueError(f"Duplicate verified copy: {record['asset_path']}")
        verified[record['asset_path']] = record
    return verified, records


def index(ref, output, copies_path=None):
    commit = git('rev-parse', '--verify', '--end-of-options', f'{ref}^{{commit}}').decode().strip()
    entries = tree(commit)
    copies, copy_records = verified_copies(copies_path or ROOT / 'docs/assets/copies.json')
    output.mkdir(parents=True, exist_ok=False)
    assets = []
    third_party = {}
    for item in entries:
        path = item['path']
        kind = asset_kind(path)
        if kind:
            copy = copies.get(path)
            if copy and copy['git_blob_sha1'] != item['oid']:
                raise ValueError(f'External copy does not match this Git version: {path}')
            assets.append({'path': path, 'kind': kind, 'git_blob_sha1': item['oid'],
                           'rights_status': 'review-required', 'external_copy': copy['url'] if copy else '',
                           'external_sha256': copy['sha256'] if copy else ''})
        parts = PurePosixPath(path).parts
        if len(parts) < 4 or parts[:2] != ('src', 'repos'):
            continue
        if parts[2] == 'notes':
            continue
        entry = third_party.setdefault(parts[2], {'path': '/'.join(parts[:3]), 'license_paths': [],
                                                  'license_labels': [], 'nested_license_count': 0})
        if parts[-1].lower().startswith(LICENSE_NAMES):
            if len(parts) == 4:
                entry['license_paths'].append(path)
                content = git('cat-file', 'blob', item['oid']).decode(errors='replace')
                entry['license_labels'].append(license_label(content))
            else:
                entry['nested_license_count'] += 1
    vendors = []
    for name, entry in sorted(third_party.items()):
        vendors.append({'name': name, 'path': entry['path'], 'root_license_paths': ';'.join(entry['license_paths']),
                        'license_text_labels': ';'.join(entry['license_labels']) or 'no-root-license-found',
                        'nested_license_count': entry['nested_license_count'],
                        'provenance_index': 'src/repos/REPOSITORIES.md', 'disposition': 'retain; review before extraction'})
    write_csv(output / 'assets.csv', ['path', 'kind', 'git_blob_sha1', 'rights_status', 'external_copy', 'external_sha256'], assets)
    write_csv(output / 'third-party.csv', ['name', 'path', 'root_license_paths', 'license_text_labels',
                                         'nested_license_count', 'provenance_index', 'disposition'], vendors)
    summary = {'source_commit': commit, 'tracked_entries': len(entries),
               'asset_counts': dict(sorted(Counter(row['kind'] for row in assets).items())),
               'third_party_directories': len(vendors),
               'without_root_license': [row['path'] for row in vendors if not row['root_license_paths']],
               'external_copy_candidates': len(copy_records), 'verified_external_copies': len(copies),
               'migrated_assets': len(set(copies) - {entry['path'] for entry in entries}),
               'root_license_present': any(row['path'].lower() in ('license', 'license.md', 'license.txt') for row in entries),
               'identity': 'Git blob SHA1 identifies repository content; external SHA256 remains blank until a verified migration.'}
    (output / 'inventory.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--output', type=Path, required=True, help='New inventory directory')
    parser.add_argument('--copies', type=Path, help='Copy registry; defaults to docs/assets/copies.json')
    args = parser.parse_args()
    index(args.ref, args.output, args.copies)


if __name__ == '__main__':
    main()
