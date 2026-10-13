"""Export hash-checked immutable research records as versioned offline JSON shards."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
import numpy as np
from import_data import safe_name, EXPECTED_SHA256

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MANIFEST_SHA256 = 'ed710b4a6e12ba4240f0416afd9aed5428a6608ed7d4f58eb0caaa6a2ec91987'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def js_safe(value):
    if isinstance(value, dict):
        return {k: js_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [js_safe(v) for v in value]
    if isinstance(value, int) and abs(value) > 2**53 - 1:
        return str(value)
    return value

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(js_safe(value), ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(data, encoding='utf-8')
    tmp.replace(path)

def rows(path):
    with path.open(encoding='utf-8', newline='') as f:
        result = list(csv.DictReader(f))
    for row in result:
        for key, value in row.items():
            try:
                row[key] = int(value)
            except ValueError:
                try:
                    row[key] = float(value)
                except ValueError:
                    row[key] = value if value != '' else None
    return result

def verified_sources(research, artifacts, expected_manifest_sha=EXPECTED_MANIFEST_SHA256):
    if sha(research / 'MANIFEST.json') != expected_manifest_sha:
        raise ValueError('MANIFEST hash differs from the original verified ZIP')
    manifest = read(research / 'MANIFEST.json')['files']
    actual = {p.relative_to(research).as_posix() for p in research.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != set(manifest) | {'MANIFEST.json'}:
        raise ValueError('Research membership differs from MANIFEST (extra or missing file)')
    for name, entry in manifest.items():
        safe_name(name)
        p = research / name
        if p.is_symlink() or research.resolve() not in p.resolve().parents or not p.is_file() or p.stat().st_size != entry['bytes'] or sha(p) != entry['sha256']:
            raise ValueError(f'Research integrity mismatch: {name}; refusing conversion')
    imported = read(artifacts / 'import_report.json')
    if imported.get('status') != 'PASS' or imported.get('archive_sha256') != EXPECTED_SHA256:
        raise ValueError('A successful import of the original ZIP is required')
    validation_path = artifacts / 'validation_report.json'
    validation = read(validation_path) if validation_path.exists() else dict(status='PENDING', scope='Full project validation in progress')
    if validation.get('status') == 'FAIL':
        raise ValueError('Scientific validation failed; refusing to publish derived data')
    if validation.get('status') == 'PASS':
        expected = ['MANIFEST.json','FREEZE.json','MODEL.json','MODEL_FREEZE.json','PROTOCOL.json']
        if not validation.get('passed') or set(validation.get('sourceHashes',{})) != set(expected):
            raise ValueError('Validation PASS lacks source hashes or passed flag')
        for name, digest in validation['sourceHashes'].items():
            if sha(research / name) != digest:
                raise ValueError(f'Stale validation source hash: {name}')
    elif validation.get('status') != 'PENDING':
        raise ValueError('Unknown validation status')
    return manifest, imported, validation

def convert(research, output, artifacts, refresh_validation=False):
    if output.resolve() == research.resolve() or research.resolve() in output.resolve().parents:
        raise ValueError('Derived output must be outside the immutable research directory')
    manifest, imported, validation = verified_sources(research, artifacts)
    if refresh_validation:
        meta = read(output / 'meta.json')
        if meta['sources']['MANIFEST.json']['sha256'] != EXPECTED_MANIFEST_SHA256:
            raise ValueError('Exported metadata has another source manifest')
        meta['project_validation'] = validation
        meta['import_validation'] = imported
        write(output / 'meta.json', meta)
        write(output / 'validation.json', validation)
        print(json.dumps({'status':'REFRESHED','project_validation':validation['status']}))
        return
    evidence = set()
    def source(name):
        evidence.add(name)
        if name == 'MANIFEST.json':
            entry = {'sha256': sha(research / name), 'bytes': (research / name).stat().st_size}
        else:
            entry = manifest[name]
        return dict(path=name, url='/data/evidence/' + name, **entry)

    protocol = read(research / 'PROTOCOL.json')
    model = read(research / 'MODEL.json')
    freeze = read(research / 'MODEL_FREEZE.json')
    all_inputs = {p.stem: read(p) for p in sorted((research / 'inputs').glob('*.json'))}
    results = {r['instance_id']: r for split in ['train', 'confirmation', 'risk']
               for r in rows(research / f'analysis/{split}_per_stream.csv')}
    catalog = []
    runs_by_stream = {}
    for p in sorted((research / 'raw').glob('*.json')):
        raw = read(p)
        iid = raw['instance_id']
        inp = all_inputs[iid]
        npz_path = raw['trajectory_file']
        if sha(research / npz_path) != raw['trajectory_sha256']:
            raise ValueError(f'Trajectory SHA mismatch: {npz_path}')
        if raw['status'] != 'complete' or raw['steps'] != len(inp['items']):
            raise ValueError(f'Incomplete run: {p.name}')
        provenance = dict(input=source(f'inputs/{iid}.json'), record=source(f'raw/{p.name}'),
                          trajectory=source(npz_path), model=source('MODEL.json'),
                          protocol=source('PROTOCOL.json'), freeze=source('MODEL_FREEZE.json'))
        decision = raw.get('decision')
        if decision:
            decision = dict(decision, feature_names=protocol['features']['names'],
                neighbor_rows=[dict(index=int(idx), instance_id=freeze['training_rows'][idx],
                    family=all_inputs[freeze['training_rows'][idx]]['family'],
                    order=all_inputs[freeze['training_rows'][idx]]['order'],
                    labels=model['y'][idx], squared_distance=decision['squared_distances'][j],
                    source=source(f"inputs/{freeze['training_rows'][idx]}.json"))
                    for j, idx in enumerate(decision['neighbors'])])
            write(output / 'decisions' / f'{iid}.json', dict(schema_version=1, instance_id=iid,
                  **decision, selector_consumed_count=raw['selector_consumed_count'], source=provenance))
        with np.load(research / npz_path, allow_pickle=False) as data:
            arrays = {key: data[key].tolist() for key in data.files}
        run = dict(raw, schema_version=1, run_id=p.stem, capacity=inp['capacity'],
                   items=inp['items'], source=provenance, **arrays)
        if decision:
            run['decision'] = decision
        dest = output / 'runs' / f'{p.stem}.json'
        write(dest, run)
        summary = {k: run.get(k) for k in ['run_id','policy','branch','used_bins','status','steps']}
        summary.update(data_url=f'/data/runs/{p.stem}.json', sha256=sha(dest), source=provenance)
        runs_by_stream.setdefault(iid, []).append(summary)
    for iid, inp in all_inputs.items():
        src = source(f'inputs/{iid}.json')
        write(output / 'inputs' / f'{iid}.json', dict(inp, schema_version=1, source=src))
        row = {k: inp.get(k) for k in ['instance_id','group_id','family','split','order','replicate','n','capacity','multiset_sha256']}
        row.update(results=results[iid], runs=runs_by_stream[iid], source=src,
                   input_url=f'/data/inputs/{iid}.json',
                   decision_url=f'/data/decisions/{iid}.json' if any(r['policy']=='SELECTOR' for r in runs_by_stream[iid]) else None)
        catalog.append(row)
    write(output / 'catalog.json', dict(schema_version=1, streams=catalog))
    write(output / 'cells.json', dict(schema_version=1, cells=rows(research / 'analysis/family_order_summary.csv'),
                                    source=source('analysis/family_order_summary.csv')))
    sources = {name: source(name) for name in ['MANIFEST.json','FREEZE.json','MODEL.json','MODEL_FREEZE.json',
                'PROTOCOL.json','analysis/SUMMARY.json','analysis/train_per_stream.csv',
                'analysis/confirmation_per_stream.csv','analysis/risk_per_stream.csv',
                'analysis/cluster_bootstrap.npz','independent_audit/FINAL_AUDIT.json',
                'independent_audit/FINAL_AUDIT.md','independent_audit/DELIVERY_AUDIT.json',
                'COST_LEDGER.json','REPORT_ZH.md','README.md']}
    meta = dict(schema_version=1, counts=dict(streams=len(catalog),runs=sum(len(s['runs']) for s in catalog),
           streams_by_split=dict(Counter(s['split'] for s in catalog)),
           runs_by_split={split:sum(len(s['runs']) for s in catalog if s['split']==split) for split in ['train','confirmation','risk']}),
           summary=read(research / 'analysis/SUMMARY.json'),
           protocol={k:v for k,v in protocol.items() if k not in ['instances']}, model=model,
           training_rows=freeze['training_rows'], sources=sources,
           historical_audit=read(research / 'independent_audit/FINAL_AUDIT.json'),
           import_validation=imported, project_validation=validation)
    for name in evidence:
        dest = output / 'evidence' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(research / name, dest)
    write(output / 'meta.json', meta)
    write(output / 'validation.json', validation)
    print(json.dumps(dict(status='EXPORTED', counts=meta['counts'], project_validation=validation.get('status'),
                         output=str(output)), ensure_ascii=False))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--research', type=Path, default=ROOT / 'research')
    p.add_argument('--output', type=Path, default=ROOT / 'public/data')
    p.add_argument('--artifacts', type=Path, default=ROOT / 'artifacts')
    p.add_argument('--refresh-validation', action='store_true', help='Update validated metadata only; retain existing trajectory shards')
    a = p.parse_args()
    convert(a.research, a.output, a.artifacts, a.refresh_validation)
