#!/usr/bin/env python3
"""Recover pinned PyVRP wheels from the repository's reviewed r1 archive offline."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive', type=Path, help='Pinned PREEXEC or final r1 archive; offline only')
parser.add_argument('--destination', type=Path, required=True, help='New directory, outside historical evidence')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[3]
archive = args.archive or repo/'experiments/results/路线求解/公共路线强基线.zip'
if sys.version_info[:2] != (3, 12):
    raise SystemExit('Archived wheels require Python 3.12')
if hashlib.sha256(archive.read_bytes()).hexdigest() not in {
    '50f01f3c345e12add88bdcfa76189e2f8ef83fde4fd5675d60c41bbf8275d067',
    'aa69e11a39891b4b6312a21b60ea14349dd18d9e16eb29f07cc4d6a21752cc8e'}:
    raise SystemExit('r1 source archive hash mismatch')
args.destination.mkdir(parents=True, exist_ok=False)
wheels = args.destination/'wheels'
wheels.mkdir()
with zipfile.ZipFile(archive) as z:
    prefix = 'public_route_strong_baseline_20261009_r1/environment/'
    for member in z.namelist():
        if member.startswith(prefix+'wheels/') and member.endswith('.whl'):
            (wheels/Path(member).name).write_bytes(z.read(member))
    lock = args.destination/'requirements.lock'
    lock.write_bytes(z.read(prefix+'requirements.lock'))
venv = args.destination/'venv'
subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
subprocess.run([str(venv/'bin/python'),'-m','pip','install','--no-index','--require-hashes',
                '--find-links',str(wheels),'-r',str(lock)],check=True)
print(venv/'bin/python')
