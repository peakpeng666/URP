"""Verify the exact project-local TF2 candidate and system ABI before using it."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def verified_candidate():
    manifest = json.loads((BASE / 'tf2-overlay-manifest.json').read_text())
    candidate = BASE / manifest['candidate_library']
    files = {**manifest['system_libraries'],
             str(candidate): manifest['candidate_sha256'],
             str(BASE / 'tf-repro/buffer_candidate.cpp'): manifest['source_sha256']}
    for name, expected in files.items():
        path = Path(name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('TF2 overlay fingerprint changed or file missing: ' + name +
                               '. Rebuild and revalidate explicitly; do not bypass this check.')
    return candidate


def verified_gui_lifetime():
    manifest=json.loads((BASE/'gui-overlay-manifest.json').read_text())
    for name,expected in manifest['files'].items():
        path=Path(name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise RuntimeError('GUI overlay fingerprint changed or file missing: '+name+
                               '. Rebuild and revalidate explicitly; do not bypass this check.')
    return BASE/manifest['library']


if __name__ == '__main__':
    print(verified_candidate())
