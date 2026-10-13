#!/usr/bin/env python3
"""Restore selected research materials from the verified complete archive."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ('data', 'papers', 'experiments', 'literature/教材', 'src/repos',
            'src/backend/backend_data')
SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'dist'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--include', nargs='+', default=PREFIXES)
    parser.add_argument('--list', action='store_true', help='Inspect without extracting')
    args = parser.parse_args()
    for prefix in args.include:
        path = PurePosixPath(prefix)
        if path.is_absolute() or '..' in path.parts or not any(
                prefix == allowed or prefix.startswith(allowed + '/') for allowed in PREFIXES):
            parser.error('Include paths must be inside the research material directories')
    expected = json.loads((ROOT / 'storage.json').read_text())['archive']
    if args.archive.stat().st_size != expected['bytes']:
        raise SystemExit('Archive size differs from storage.json')
    digest = hashlib.sha256()
    with args.archive.open('rb') as reader:
        for block in iter(lambda: reader.read(8 * 1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != expected['sha256']:
        raise SystemExit('Archive SHA-256 differs from storage.json')
    tracked = set(subprocess.check_output(
        ['git', '-C', str(ROOT), 'ls-files', '-z']).decode().split('\0'))
    plan = []
    with zipfile.ZipFile(args.archive) as archive:
        for member in archive.infolist():
            original = PurePosixPath(member.filename)
            if '..' in original.parts or original.is_absolute() or '\\' in member.filename:
                raise SystemExit('Unsafe archive member')
            if not original.parts or original.parts[0] != 'URP' or len(original.parts) == 1:
                continue
            relative = PurePosixPath(*original.parts[1:])
            name = str(relative)
            if member.is_dir() or name in tracked or SKIP.intersection(relative.parts):
                continue
            if not any(name == prefix or name.startswith(prefix + '/') for prefix in args.include):
                continue
            if stat.S_ISLNK(member.external_attr >> 16):
                continue
            destination = ROOT.joinpath(*relative.parts)
            if ROOT not in destination.resolve().parents:
                raise SystemExit('Destination escapes the project')
            if destination.exists():
                crc = 0
                if destination.is_file():
                    with destination.open('rb') as reader:
                        for block in iter(lambda: reader.read(1024 * 1024), b''):
                            crc = zlib.crc32(block, crc)
                if not destination.is_file() or destination.stat().st_size != member.file_size or crc != member.CRC:
                    raise SystemExit(f'Local material differs from the archive: {relative}')
                continue
            plan.append((member, destination))
        total = sum(member.file_size for member, _ in plan)
        print(json.dumps({'files': len(plan), 'bytes': total, 'archive_sha256': 'PASS'},
                         ensure_ascii=False))
        if args.list:
            return
        if shutil.disk_usage(ROOT).free < total:
            raise SystemExit('Insufficient free space')
        for member, destination in plan:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as reader, destination.open('wb') as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
            mode = (member.external_attr >> 16) & 0o777
            if mode:
                destination.chmod(mode)
    print('Materials restored')


if __name__ == '__main__':
    main()
