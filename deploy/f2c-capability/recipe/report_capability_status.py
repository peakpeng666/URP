#!/usr/bin/env python3
"""Only finite, indexed capability labels may leave private evidence."""
import json
import os
from pathlib import Path
import re
import stat

STAGES=('checkout','anchor','helper_tests','authentication','capability')
OUTCOMES={'success','failure','cancelled','skipped',''}

def unique(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError('Duplicate key')
        out[k]=v
    return out

def read_bounded(path, limit):
    path=Path(path)
    for parent in path.parents:
        if parent.is_symlink(): raise ValueError('Unsafe parent')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>limit:
            raise ValueError('Unsafe file')
        raw=os.read(fd,limit+1)
        after=os.fstat(fd)
        if len(raw)>limit or len(raw)!=before.st_size or any(getattr(before,k)!=getattr(after,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')):
            raise ValueError('Changed file')
        return json.loads(raw,object_pairs_hook=unique)
    finally: os.close(fd)

def project(root, outcomes, code_bytes):
    if set(outcomes)!=set(STAGES) or any(not isinstance(v,str) or v not in OUTCOMES for v in outcomes.values()):
        return 'stage=report status=FAIL code=UNKNOWN'
    stage=next((s for s in STAGES if outcomes[s]!='success'),None)
    if stage in {'checkout','anchor','helper_tests'}:
        return 'stage='+stage+' status=FAIL code='+stage.upper()+'_FAILED'
    try:
        if not isinstance(code_bytes,bytes) or len(code_bytes)>16384: raise ValueError('Bad code bytes')
        codes=json.loads(code_bytes,object_pairs_hook=unique)
        if set(codes)!={'schema','authentication','capability'} or type(codes['schema']) is not int or codes['schema']!=1:
            raise ValueError('Bad code set')
        for name in ('authentication','capability'):
            row=codes[name]
            if set(row)!={'pass_code','codes'} or not isinstance(row['codes'],list) or not 1<=len(row['codes'])<=128:
                raise ValueError('Bad code set')
            if any(not isinstance(c,str) or not re.fullmatch('[A-Z][A-Z0-9_]{0,79}',c) for c in row['codes']):
                raise ValueError('Bad code set')
            if len(set(row['codes']))!=len(row['codes']) or row['pass_code'] not in row['codes']:
                raise ValueError('Bad code set')
        records={}
        for name,file in (('authentication','capability-preparation-status.json'),('capability','capability-probe-status.json')):
            if stage and name!=stage: continue
            row=read_bounded(Path(root)/file,4096)
            if set(row)!={'schema','status','code'} or type(row['schema']) is not int or row['schema']!=1:
                raise ValueError('Bad receipt')
            if row['status'] not in {'PASS','FAIL'} or row['code'] not in codes[name]['codes']:
                raise ValueError('Bad receipt')
            if (row['status']=='PASS') != (row['code']==codes[name]['pass_code']):
                raise ValueError('Contradictory receipt')
            records[name]=row
        if stage:
            row=records[stage]
            if row['status']!='FAIL': raise ValueError('Outcome mismatch')
            return 'stage='+stage+' status=FAIL code='+row['code']
        if any(row['status']!='PASS' for row in records.values()): raise ValueError('Outcome mismatch')
        return 'stage=capability status=PASS code='+codes['capability']['pass_code']
    except Exception:
        return 'stage='+(stage or 'report')+' status=FAIL code=UNKNOWN'

def main():
    root=Path(__file__).resolve().parent.parent
    outcomes={s:os.environ.get('OUTCOME_'+s.upper(),'') for s in STAGES}
    print(project(root,outcomes,globals().get('_VERIFIED_PUBLIC_CODES_BYTES')))

if __name__ in {'__main__','verified_capability_report'}: main()
