"""Verify an immutable research ZIP before safe extraction. Never executes its code."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = '5f47d49fade8f926bb5751818b038288a772b711d4249d70a7a392eeb9719350'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def safe_name(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or path.is_absolute() or '..' in path.parts or ':' in name:
        raise ValueError(f'Unsafe archive path: {name}')
    return path

def import_archive(archive: Path, target: Path, report: Path, expected=EXPECTED_SHA256):
    archive_sha = digest(archive.read_bytes())
    if archive_sha != expected:
        raise ValueError(f'ZIP SHA256 mismatch: {archive} {archive_sha}')
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP paths')
        for info in infos:
            safe_name(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16) or info.is_dir():
                raise ValueError(f'Unexpected non-regular archive member: {info.filename}')
        manifest_bytes = z.read('MANIFEST.json')
        manifest = json.loads(manifest_bytes)['files']
        if set(names) != set(manifest) | {'MANIFEST.json'}:
            raise ValueError('MANIFEST membership differs from ZIP')
        # Complete validation occurs before the first write to the extraction tree.
        for name, entry in manifest.items():
            data = z.read(name)
            if len(data) != entry['bytes'] or digest(data) != entry['sha256']:
                raise ValueError(f'MANIFEST mismatch: {name}')
        target = target.resolve()
        for name in names:
            dest = target.joinpath(*safe_name(name).parts)
            if target not in dest.resolve().parents:
                raise ValueError(f'Extraction escapes destination: {name}')
            if dest.exists() and (not dest.is_file() or digest(dest.read_bytes()) != digest(z.read(name))):
                raise ValueError(f'Existing research file changed; refusing overwrite: {dest}')
        for name in names:
            dest = target.joinpath(*safe_name(name).parts)
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(name))
    result = dict(schema_version=1, status='PASS', created_utc=datetime.now(timezone.utc).isoformat(),
                  archive_sha256=archive_sha, archive_bytes=archive.stat().st_size,
                  zip_members=len(names), manifest_entries=len(manifest), manifest_sha256=digest(manifest_bytes),
                  count_note='MANIFEST.json is the sole member not listed in itself',
                  scope='ZIP integrity, safe paths, all member hashes; scientific replay is separate')
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path)
    p.add_argument('--target', type=Path, default=ROOT / 'research')
    p.add_argument('--report', type=Path, default=ROOT / 'artifacts/import_report.json')
    a = p.parse_args()
    archive = a.archive or next((ROOT / 'inputs').glob('*.zip'), None)
    if archive is None:
        p.error('Place the original ZIP in inputs/ or supply --archive')
    print(json.dumps(import_archive(archive, a.target, a.report), ensure_ascii=False, indent=2))
