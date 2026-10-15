"""Verify, and build if needed, the project-local parameter_bridge exit guard before it is preloaded."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'native' / 'bridge-exit-guard.json'
LIBRARY = HERE.parent / 'runtime' / 'native' / 'liburp_bridge_exit_guard.so'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified_bridge_guard():
    manifest = json.loads(MANIFEST.read_text())
    source = HERE / 'native' / 'bridge_exit_guard.c'
    expected = {str(source): manifest['source_sha256'], **manifest['validated_against']}
    for name, digest in expected.items():
        path = Path(name)
        if not path.is_file() or _sha(path) != digest:
            raise RuntimeError('Bridge exit guard fingerprint changed or file missing: ' + name +
                               '. Rebuild and revalidate explicitly (src/lab/ros/native/build.sh and '
                               'setup/2026-10-15/integration/bridge-exit/repro.py); do not bypass this check.')
    if not LIBRARY.is_file() or LIBRARY.stat().st_mtime < source.stat().st_mtime:
        subprocess.run(['bash', str(HERE / 'native' / 'build.sh')], check=True, capture_output=True)
    built = json.loads((LIBRARY.parent / 'bridge-exit-guard-manifest.json').read_text())
    if (built['library_sha256'] != _sha(LIBRARY) or built['source_sha256'] != manifest['source_sha256']
            or built['validated_against'] != manifest['validated_against']):
        raise RuntimeError('Bridge guard binary/build fingerprint mismatch; explicit rebuild and revalidation required')
    return LIBRARY


if __name__ == '__main__':
    print(verified_bridge_guard())
