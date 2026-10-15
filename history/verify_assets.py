#!/usr/bin/env python3
"""Read-only verification of inherited research asset Git blob IDs; no experiments run."""
import csv, hashlib, json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
failures=[]; checked=0
for manifest in sorted((HERE/'manifests').glob('assets-*.csv')):
    with manifest.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            p=ROOT/row['path']
            if not p.exists() and not p.is_symlink():
                failures.append({'path':row['path'],'reason':'missing'});continue
            if p.is_symlink():
                data=os.readlink(p).encode(); size=len(data)
                h=hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data)
            else:
                size=p.stat().st_size
                h=hashlib.sha1(b'blob '+str(size).encode()+b'\0')
                with p.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024*1024),b''):h.update(chunk)
            checked+=1
            if h.hexdigest()!=row['git_blob_sha1']:
                failures.append({'path':row['path'],'reason':'blob_hash_mismatch'})
            if row['size_bytes'] and size!=int(row['size_bytes']):
                failures.append({'path':row['path'],'reason':'size_mismatch'})
print(json.dumps({'checked':checked,'failures':failures,'scientific_validation':False},ensure_ascii=False,indent=2))
raise SystemExit(bool(failures))
