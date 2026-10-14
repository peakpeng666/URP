#!/usr/bin/env python3
"""Restore exact pinned wheels to the canonical location without network or installation."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    repo = here.parents[1]
    mapping = json.loads((here / 'WHEEL_ARCHIVE_MAP.json').read_text())
    archive = args.archive or repo / mapping['archive']['repository_path']
    archive_bytes = archive.read_bytes()
    if len(archive_bytes) != mapping['archive']['bytes'] or digest(archive_bytes) != mapping['archive']['sha256']:
        raise SystemExit('Pinned original archive size or SHA256 mismatch')
    destination = args.destination or here / 'wheels'
    # Validate the whole set before writing any file. Never silently replace differing bytes.
    prepared = []
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        for row in mapping['wheels']:
            if names.count(row['archive_member']) != 1:
                raise SystemExit('Missing or duplicate archive member: ' + row['archive_member'])
            data = zf.read(row['archive_member'])
            if len(data) != row['bytes'] or digest(data) != row['sha256']:
                raise SystemExit('Pinned wheel mismatch: ' + row['filename'])
            target = destination / row['filename']
            if target.exists() and target.read_bytes() != data:
                raise SystemExit('Refusing to overwrite differing bytes: ' + str(target))
            prepared.append((target, data))
    destination.mkdir(parents=True, exist_ok=True)
    for target, data in prepared:
        if not target.exists():
            with target.open('xb') as handle:
                handle.write(data)
    print(json.dumps({'restored_or_verified': len(prepared), 'destination': str(destination),
                      'archive_sha256': mapping['archive']['sha256']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
