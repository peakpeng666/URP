"""Build and fingerprint the local Fortress encoder publication backport.

No network, sudo, installed-library replacement or environment-wide overrides.
Pure code/cloud checks never call this; torque simulation builds on demand.
"""
import hashlib
import json
from pathlib import Path
import subprocess

LAB = Path(__file__).resolve().parents[1]
SOURCE = LAB / 'ros/native/joint_state'
OUTPUT = LAB / 'runtime/native/joint_state'
LIBRARY = OUTPUT / 'liburp_joint_state.so'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure():
    sources = {p.name: sha(p) for p in SOURCE.iterdir() if p.is_file()}
    version = subprocess.run(['pkg-config', '--modversion', 'ignition-gazebo6'],
                             check=True, text=True, capture_output=True).stdout.strip()
    wanted = {'source_sha256': sources, 'gazebo_dev_version': version}
    manifest = OUTPUT / 'manifest.json'
    old = json.loads(manifest.read_text()) if manifest.is_file() else {}
    if not (LIBRARY.is_file() and all(old.get(k) == v for k, v in wanted.items())
            and old.get('library_sha256') == sha(LIBRARY)):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        commands = [['cmake', '-S', str(SOURCE), '-B', str(OUTPUT), '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                    ['cmake', '--build', str(OUTPUT), '-j2']]
        for command in commands:
            subprocess.run(command, check=True, timeout=120)
        old = {**wanted, 'library': str(LIBRARY), 'library_sha256': sha(LIBRARY),
               'scope': 'Gazebo 6.18 official joint measurements with source-time publication throttled to 50 Hz; local plugin alias'}
        manifest.write_text(json.dumps(old, indent=2)+'\n')
    return old


if __name__ == '__main__':
    print(json.dumps(ensure(), indent=2))
