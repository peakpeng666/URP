"""Future image preparation only. Pinned-action bootstrap is explicit trust, not APT provenance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

UV_ACTION='astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4'
PYTHON_KEY='cpython-3.12.13-linux-x86_64-gnu'
PYTHON_SHA='506191be3ee7bd190a8834dcdc1b3bc70aab50608deccc711935aa007239cabd'
PYTHON_URL='https://github.com/astral-sh/python-build-standalone/releases/download/20260807/cpython-3.12.13%2B20260807-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz'
ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}

def require(value, code):
    if not value: raise RuntimeError(code)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def regular(path):
    path=Path(path)
    for p in [path,*path.parents]: require(not p.is_symlink(),'BOOTSTRAP_ALIAS')
    s=path.stat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and not s.st_mode&0o6022,'BOOTSTRAP_MODE')
    require(0<s.st_size<256*1024*1024,'BOOTSTRAP_SIZE')
    return s

def version(tool,path):
    output=subprocess.check_output([str(path),'--version'],env=ENV,stdin=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True).strip()
    require(tool=='uv','BOOTSTRAP_TOOL')
    require(re.fullmatch(r'uv 0\.12\.23(?: \([^\n]{1,120}\))?',output),'UV_VERSION')
    return '0.12.23'

def validate_lock(lock):
    require(type(lock) is dict and set(lock)=={'schema','trust','tools','python'},'BOOTSTRAP_SCHEMA')
    require(lock['schema']==1 and lock['trust']=='pinned-action-bootstrap-measured-not-ubuntu-signed','BOOTSTRAP_TRUST')
    require(set(lock['tools'])=={'uv'},'BOOTSTRAP_TOOL_SET')
    for name,action in (('uv',UV_ACTION),):
        r=lock['tools'][name]
        require(type(r) is dict and set(r)=={'action','version','sha256','bytes'},'BOOTSTRAP_TOOL_SCHEMA')
        require(r['action']==action and type(r['sha256']) is str and re.fullmatch('[0-9a-f]{64}',r['sha256']),'BOOTSTRAP_SOURCE')
        require(type(r['bytes']) is int and 0<r['bytes']<256*1024*1024,'BOOTSTRAP_SIZE')
        require(r['version']=='0.12.23','BOOTSTRAP_VERSION')
    require(lock['python']=={'key':PYTHON_KEY,'url':PYTHON_URL,'sha256':PYTHON_SHA},'PYTHON_DISTRIBUTION')
    return lock

def collect(uv,destination):
    """Called only after the reviewed immutable UV action by trusted workflow code."""
    result={'schema':1,'trust':'pinned-action-bootstrap-measured-not-ubuntu-signed','tools':{},'python':{'key':PYTHON_KEY,'url':PYTHON_URL,'sha256':PYTHON_SHA}}
    for name,path,action in (('uv',uv,UV_ACTION),):
        s=regular(path); digest=sha(path); ver=version(name,path)
        # Access time may change when hashing or running --version. Keep all
        # stable identity/mutation fields and the independent digest reread.
        fields=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
        reread=sha(path);after=regular(path)
        require(reread==digest and tuple(getattr(after,k) for k in fields)==tuple(getattr(s,k) for k in fields),'BOOTSTRAP_CHANGED')
        result['tools'][name]={'action':action,'version':ver,'sha256':digest,'bytes':s.st_size}
    validate_lock(result)
    with Path(destination).open('x') as f: json.dump(result,f,sort_keys=True,indent=2); f.write('\n')
    return sha(destination)

def install(lock_path,expected):
    """Trusted image root stage, never called by local fixtures."""
    # Container placement is established by the external Docker build controller;
    # /.dockerenv is neither portable under BuildKit nor a security proof.
    require(os.getuid()==0,'IMAGE_ROOT_ONLY')
    release=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    require(release.get('ID','').strip(chr(34))=='ubuntu' and release.get('VERSION_ID','').strip(chr(34))=='22.04','IMAGE_DISTRIBUTION')
    require(re.fullmatch('[0-9a-f]{64}',expected) and sha(lock_path)==expected,'BOOTSTRAP_LOCK_ANCHOR')
    lock=validate_lock(json.loads(Path(lock_path).read_bytes()))
    for name,path in (('uv',Path('/opt/urp-uv/uv')),):
        r=lock['tools'][name]; s=regular(path)
        require(s.st_size==r['bytes'] and sha(path)==r['sha256'],'BOOTSTRAP_BYTES')
        require(version(name,path)==r['version'],'BOOTSTRAP_VERSION')
    prefix=Path('/opt/urp-python'); staging=Path('/opt/urp-python-downloads')
    require(not prefix.exists() and not staging.exists(),'FRESH_PYTHON_REQUIRED')
    env={**ENV,'HOME':'/root','UV_PYTHON_INSTALL_DIR':str(staging),'UV_NO_CACHE':'1','UV_NO_PROGRESS':'1','UV_NO_ENV_FILE':'1'}
    # Exact baseline selector uses the hash-bound distribution embedded in uv0.12.23.
    # uv verifies its embedded archive SHA; the independently pinned row above binds
    # that distribution. This does not claim an Ubuntu-signed CPython package.
    subprocess.run(['/opt/urp-uv/uv','python','install',PYTHON_KEY],env=env,stdin=subprocess.DEVNULL,check=True)
    selected=staging/PYTHON_KEY
    require(selected.is_dir() and not selected.is_symlink(),'PYTHON_INSTALL_LAYOUT')
    selected.rename(prefix)
    python=prefix/'bin/python3.12'
    actual=subprocess.check_output([str(python),'-I','-B','-S','-c','import platform;print(platform.python_version())'],env=ENV,text=True).strip()
    require(actual=='3.12.13','PYTHON_VERSION')
    receipt={'schema':1,'tools':{}}
    for name,path in (('uv','/opt/urp-uv/uv'),('python',str(python))):
        prov=({'kind':'uv-pinned-download','archive_sha256':PYTHON_SHA,'key':PYTHON_KEY} if name=='python' else {'kind':'pinned-github-action','action':lock['tools'][name]['action']})
        receipt['tools'][name]={'path':path,'version':actual if name=='python' else lock['tools'][name]['version'],'sha256':sha(path),'provenance':prov}
    with Path('/inputs/bootstrap-tools.json').open('x') as f: json.dump(receipt,f,sort_keys=True,indent=2);f.write('\n')

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    c=sub.add_parser('collect'); c.add_argument('--uv',type=Path,required=True);c.add_argument('--output',type=Path,required=True)
    i=sub.add_parser('install');i.add_argument('--lock',type=Path,required=True);i.add_argument('--expected-sha256',required=True)
    a=p.parse_args()
    if a.mode=='collect': print(collect(a.uv,a.output))
    else: install(a.lock,a.expected_sha256)
if __name__=='__main__':main()
