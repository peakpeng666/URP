"""Trusted preparation final step. Measures inputs; does not execute them.
Caller must anchor the reviewed source/preparer before using this derived index.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
# Safe under Python -I: load only this reviewed sibling, never cwd/site modules.
import importlib.util
_spec=importlib.util.spec_from_file_location('engine_gate',Path(__file__).resolve().with_name('engine_gate.py'))
_gate=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_gate)
PROTOCOL,require=_gate.PROTOCOL,_gate.require

def freeze(root,phase):
    require(root.is_absolute() and root==root.resolve(),'canonical input root')
    destination=root/'input-index.json';require(not destination.exists() and not destination.is_symlink(),'never replace an input index')
    files={}
    for p in sorted(root.rglob('*')):
        name=str(p.relative_to(root));mode=p.lstat().st_mode
        require(stat.S_ISLNK(mode) or not mode & 0o022,'writable input member')
        if stat.S_ISDIR(mode):continue
        require(p.resolve().is_relative_to(root),'alias escapes root')
        if p.is_symlink():
            target=p.readlink().as_posix()
            require(not target.startswith('/'),'absolute source alias')
            row={'symlink':target,'sha256':hashlib.sha256(target.encode()).hexdigest()}
        else:
            require(p.is_file() and stat.S_ISREG(mode),'nonregular input member')
            row={'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        files[name]=row
    entry='offline_build.py' if phase=='build' else 'validation/run_pipeline.py'
    require(entry in files and 'engine_gate.py' in files,'phase entrypoint missing')
    index={'schema':1,'protocol':PROTOCOL,'application_commit':'3acf840d1a0c16ab1cfcca15744e4ea6609ddb35',
        'python':'/opt/urp-python/bin/python3.12','files':files,
        'commands':{phase:['/opt/urp-python/bin/python3.12','-I','-B','/inputs/'+entry]}}
    with destination.open('x') as f:json.dump(index,f,sort_keys=True,indent=2);f.write('\n')
    return hashlib.sha256(destination.read_bytes()).hexdigest()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--phase',choices=['build','validate'],required=True)
    a=p.parse_args();print(freeze(a.root,a.phase))
