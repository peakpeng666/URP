"""Bind the authenticated bootstrap transaction to the later full signed closure."""
import hashlib
import importlib.util
import json
from pathlib import Path


def require(value,code):
    if not value:raise RuntimeError(code)

def verify_system_ca():
    # Exact source-indexed sibling; -I remains enabled and no search path changes.
    path=Path(__file__).parent/'bootstrap'/'provision_system_ca.py'
    spec=importlib.util.spec_from_file_location('urp_verified_system_ca',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.verify()

def verify(bootstrap,packages):
    receipt=json.loads((bootstrap/'bootstrap.json').read_bytes())
    require(receipt['status']=='bootstrap-installed-transaction-verified' and receipt['transaction_authenticated'] is True,'BOOTSTRAP_RECEIPT')
    require(receipt['snapshot']=='20261021T000000Z' and receipt['full_closure_verified'] is False,'BOOTSTRAP_SCOPE')
    require(packages['installed'] is True and packages['signed_metadata_verified'] is True and packages['closure_complete'] is True,'FULL_CLOSURE_REQUIRED')
    require(packages['snapshot']=={'kind':'immutable-signed-snapshot','identifier':'20261021T000000Z'},'SNAPSHOT_BINDING')
    resolved={}
    for r in packages['resolved']:
        require(r['name'] not in resolved,'DUPLICATE_PACKAGE');resolved[r['name']]=r
    root_rows=[line.split('\t') for line in (bootstrap/'roots.tsv').read_text().splitlines()]
    require(all(len(row)==2 for row in root_rows),'BOOTSTRAP_ROOT_SCHEMA')
    roots={row[0] for row in root_rows}
    require(len(root_rows)==len(roots),'BOOTSTRAP_ROOT_DUPLICATE')
    require(roots=={'python3','python3-apt','ca-certificates'},'BOOTSTRAP_ROOTS')
    selected=set(roots)
    transaction=[]
    for line in (bootstrap/'transaction.tsv').read_text().splitlines():
        row=line.split('\t');require(len(row)==10,'BOOTSTRAP_TRANSACTION_SCHEMA')
        name,arch,version,old,action,filename,size,digest,suite,component=row
        require(name not in transaction and action in ('install','upgrade'),'BOOTSTRAP_TRANSACTION_ACTION')
        transaction.append(name);selected.add(name)
        require(name in resolved,'BOOTSTRAP_PACKAGE_OUTSIDE_CLOSURE')
        target=resolved[name]
        # The snapshot remains identical: no silently changed bootstrap provider.
        require(target['architecture']==arch and target['version']==version and target['archive_filename']==filename and target['archive_sha256']==digest and target['archive_size']==int(size),'BOOTSTRAP_PROVIDER_CHANGED')
    require(selected.issubset(resolved),'BOOTSTRAP_ROOT_OUTSIDE_CLOSURE')
    require(all(resolved[name]['version']==version for name,version in root_rows),'BOOTSTRAP_ROOT_VERSION_CHANGED')
    system_ca=verify_system_ca()
    rows={}
    for p in sorted(bootstrap.rglob('*')):
        require(not p.is_symlink(),'BOOTSTRAP_EVIDENCE_ALIAS')
        if p.is_file():rows[p.relative_to(bootstrap).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        else:require(p.is_dir(),'BOOTSTRAP_EVIDENCE_SPECIAL')
    return {'schema':1,'status':'bootstrap-transaction-bound-to-full-closure','bootstrap_packages':sorted(selected),'bootstrap_evidence':rows,'derived_system_ca':system_ca,'compiler_build_executed':False}

def main():
    bootstrap=Path('/opt/urp-bootstrap-evidence');root=Path('/inputs')
    result=verify(bootstrap,json.loads((root/'package-preparation.json').read_bytes()))
    with (root/'bootstrap-closure.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
if __name__=='__main__':main()
