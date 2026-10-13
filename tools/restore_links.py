#!/usr/bin/env python3
"""Restore project-local directory links after a Google Drive folder download."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKS = {
    'src/backend/packages': '../../data/packages',
    'src/frontend/inputs': '../../data/bpp/inputs',
    'src/frontend/research': '../../data/bpp/records',
    'src/frontend/public/data': '../../../data/bpp/exports',
}

def main():
    for name, target in LINKS.items():
        path = ROOT / name
        if path.is_symlink() and path.readlink() == Path(target):
            print(f'OK {name}')
            continue
        if path.exists() or path.is_symlink():
            raise SystemExit(f'Existing different path: {name}')
        if not (path.parent / target).is_dir():
            raise SystemExit(f'Missing target: {name} -> {target}')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target, target_is_directory=True)
        print(f'Created {name} -> {target}')

if __name__ == '__main__':
    main()
