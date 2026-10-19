#!/usr/bin/env python3
"""Run with src/lab/.venv/bin/python; verify the binding bytes AND dynamic load."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'src/lab/vendor/fields2cover-manifest.json').read_text())
    try:
        import fields2cover as f2c
        binary = Path(f2c.__file__).parent / '_fields2cover_python.so'
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        if digest != manifest['binary_sha256']:
            raise ValueError('installed extension SHA256 differs from the accepted manifest')
        if importlib.metadata.version('fields2cover') != manifest['version']:
            raise ValueError('installed Fields2Cover version differs from the manifest')
        point = f2c.Point(1.0, 2.0)
        if (point.getX(), point.getY()) != (1.0, 2.0):
            raise ValueError('native Point roundtrip failed')
    except (ImportError, OSError, ValueError, AttributeError) as exc:
        print(f'Fields2Cover load check failed: {exc}. The pinned wheel needs Ubuntu 22.04 amd64, '
              'CPython 3.12 and deploy/fields2cover-packages.txt libraries.', file=sys.stderr)
        return 1
    print(json.dumps(dict(passed=True, scope='binding fingerprint/load/Point smoke only',
                         version=manifest['version'], binary_sha256=digest)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
