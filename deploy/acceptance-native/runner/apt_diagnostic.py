#!/usr/bin/env python3
"""Read-only APT solver after install failure; stdout must remain private."""
import os, pathlib, re, subprocess, sys
TARGET='94420cf3b703c564134048e1b074406df901bba3'
BASE=['python3','curl','ca-certificates','gnupg','git','zstd']

def solver_command(source):
    source=pathlib.Path(source)
    def git(*args):return subprocess.check_output(['git','-C',str(source),*args],stderr=subprocess.DEVNULL)
    if git('rev-parse','HEAD').decode().strip()!=TARGET:raise ValueError('source_revision_mismatch')
    raw=(source/'deploy/ros-packages.txt').read_bytes()
    if raw!=git('show',TARGET+':deploy/ros-packages.txt'):raise ValueError('tracked_blob_mismatch')
    packages=[x for x in raw.decode().splitlines() if not re.match(r'^\s*(#|$)',x)]
    if not all(re.fullmatch(r'[a-z0-9][a-z0-9+.-]*',x) for x in packages):raise ValueError('invalid_package_list')
    return ['apt-get','--simulate','-o','Debug::pkgProblemResolver=yes','install','--no-install-recommends',*BASE,*packages]

def diagnose(source):
    # No sudo, no update/download/install action: simulation explicitly disables locks.
    env=dict(os.environ,LC_ALL='C',LANG='C')
    try:
        result=subprocess.run(solver_command(source),env=env,timeout=90,check=False)
        print('URP_APT_SOLVER_EXIT_'+str(result.returncode),flush=True)
    except subprocess.TimeoutExpired:print('URP_APT_SOLVER_TIMEOUT',flush=True)

if __name__=='__main__':diagnose(sys.argv[1])
