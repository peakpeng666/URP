#!/usr/bin/env python3
"""Authenticate EXISTING tools for a separate future namespace capability probe.

No APT transaction, helper invocation, namespace operation, package script, or
rootfs creation. The initial system Python and read-only dpkg/gpgv/dpkg-deb are
explicit bootstrap trust; this proof cannot authenticate them retroactively.
"""
import argparse
import hashlib
import types
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import struct
import subprocess
import sys
import tarfile

SNAPSHOT = '20261021T000000Z'
METADATA_SOURCE_SHA256 = '3ef3c611be036f06331e4c2f0567fa75db27072270b075c72dc1231a4644f558'
TOOLS = {'python': '/usr/bin/python3.10', 'unshare': '/usr/bin/unshare',
         'newuidmap': '/usr/bin/newuidmap', 'newgidmap': '/usr/bin/newgidmap'}
TOOL_PACKAGES = {'python': 'python3.10-minimal', 'unshare': 'util-linux',
                 'newuidmap': 'uidmap', 'newgidmap': 'uidmap'}
BOOTSTRAP_TOOLS = {'gpgv': '/usr/bin/gpgv', 'dpkg_query': '/usr/bin/dpkg-query', 'dpkg_deb': '/usr/bin/dpkg-deb'}
HOST_FILES = ('/etc/passwd', '/etc/group', '/etc/nsswitch.conf',
              '/etc/ld.so.cache', '/usr/lib/os-release', '/var/lib/dpkg/status',
              '/usr/share/keyrings/ubuntu-archive-keyring.gpg')
OPTIONAL_HOST_FILES = ('/etc/subuid', '/etc/subgid')
PYTHON_PATHS = ['/usr/lib/python310.zip', '/usr/lib/python3.10', '/usr/lib/python3.10/lib-dynload']
PYTHON_PACKAGES = ('libpython3.10-minimal', 'libpython3.10-stdlib')
PYTHON_OPTIONAL_PACKAGES = {name: 'python3.10' for name in
    ('libpython3.10-dev', 'python3.10-dev', 'libpython3.10-testsuite', 'python3.10-examples')}
PYTHON_OPTIONAL_PACKAGES.update({'python3-gdbm': 'python3-stdlib-extensions',
                                 'python3-tk': 'python3-stdlib-extensions'})
PREPARATION_CODES = frozenset({
    'CAP_INPUTS_VERIFIED', 'CAP_SOURCE_REJECTED', 'CAP_HOST_UNSUPPORTED',
    'CAP_INTERPRETER_REJECTED', 'CAP_TOOL_MISSING', 'CAP_METADATA_REJECTED',
    'CAP_PACKAGE_UNAUTHENTICATED', 'CAP_OWNER_REJECTED', 'CAP_ARCHIVE_REJECTED',
    'CAP_BYTES_REJECTED', 'CAP_MODE_REJECTED', 'CAP_RUNTIME_UNSUPPORTED',
    'CAP_RUNTIME_UNAUTHENTICATED', 'CAP_CONFIGURATION_REJECTED',
    'CAP_STATE_CHANGED', 'CAP_LOCK_REJECTED', 'CAP_IO_FAILED', 'CAP_UNEXPECTED_ERROR',
    'CAP_LOGINUID_UNSUPPORTED', 'CAP_NSCD_PRESENT', 'CAP_NSS_UNSUPPORTED', 'CAP_NSS_PROVIDER_UNAUTHENTICATED',
} | {'CAP_' + name.upper() + suffix for name in TOOLS for suffix in
     ('_MISSING', '_PACKAGE_UNAUTHENTICATED', '_OWNER_REJECTED', '_BYTES_REJECTED', '_MODE_REJECTED')})
FILE_KEYS = frozenset('path resolved_path sha256 uid gid mode device inode size nlink aliases'.split())
LIBDIRS = ('/lib/x86_64-linux-gnu', '/usr/lib/x86_64-linux-gnu', '/lib', '/usr/lib')
NSCD_SOCKET = '/var/run/nscd/socket'
NSS_SONAMES = ('libnss_systemd.so.2', 'libnss_systemd-2.35.so')


class PreparationError(RuntimeError):
    def __init__(self, code):
        if code not in PREPARATION_CODES or code == 'CAP_INPUTS_VERIFIED':
            raise ValueError('Unknown preparation code')
        super().__init__(code)
        self.code = code


def need(value, code):
    if not value:
        raise PreparationError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'CAP_LOCK_REJECTED')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def measure(path, limit=64 * 1024 * 1024, root_owned=True):
    """Measure root-owned aliases and a stable regular file, never special files."""
    path = Path(path).absolute()
    need('..' not in path.parts, 'CAP_IO_FAILED')
    aliases, todo, current, hops = [], list(path.parts[1:]), Path('/'), 0
    while todo:
        current /= todo.pop(0)
        before = current.lstat()
        if root_owned:
            need(before.st_uid == 0 and (stat.S_ISLNK(before.st_mode) or not before.st_mode & 0o022), 'CAP_MODE_REJECTED')
        if stat.S_ISLNK(before.st_mode):
            hops += 1
            need(hops <= 16, 'CAP_MODE_REJECTED')
            target = os.readlink(current)
            aliases.append({'path': str(current), 'target': target, 'uid': before.st_uid,
                            'gid': before.st_gid, 'device': before.st_dev, 'inode': before.st_ino})
            expanded = Path(os.path.normpath(str(current.parent / target)))
            todo = list(expanded.parts[1:]) + todo
            current = Path('/')
        elif todo:
            need(stat.S_ISDIR(before.st_mode), 'CAP_MODE_REJECTED')
    fd = os.open(current, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit, 'CAP_MODE_REJECTED')
        if root_owned:
            need(before.st_uid == 0 and not before.st_mode & 0o022, 'CAP_MODE_REJECTED')
        chunks, total = [], 0
        while True:
            block = os.read(fd, min(1024 * 1024, limit + 1 - total))
            if not block:
                break
            total += len(block)
            need(total <= limit, 'CAP_IO_FAILED')
            chunks.append(block)
        after = os.fstat(fd)
        need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'CAP_STATE_CHANGED')
        data = b''.join(chunks)
    finally:
        os.close(fd)
    return {'path': str(path), 'resolved_path': str(current), 'sha256': digest(data),
            'uid': before.st_uid, 'gid': before.st_gid, 'mode': stat.S_IMODE(before.st_mode),
            'device': before.st_dev, 'inode': before.st_ino, 'size': before.st_size,
            'nlink': before.st_nlink, 'aliases': aliases}, data


def source_anchor(root, expected):
    need(re.fullmatch('[0-9a-f]{64}', expected or ''), 'CAP_SOURCE_REJECTED')
    measured, raw = measure(root / 'source-index.json', 1024 * 1024, False)
    need(not measured['aliases'] and measured['nlink'] == 1 and digest(raw) == expected, 'CAP_SOURCE_REJECTED')
    index = unique_json(raw)
    need(type(index.get('schema')) is int and index.get('schema') == 1 and index.get('status') == 'reviewed-source' and
         type(index.get('files')) is dict, 'CAP_SOURCE_REJECTED')
    required = {'recipe/prepare_capability_inputs.py', 'recipe/jammy_metadata.py',
                'recipe/probe_namespace_capabilities.py'}
    need(required.issubset(index['files']), 'CAP_SOURCE_REJECTED')
    result = {'source-index.json': measured}
    for name, entry in index['files'].items():
        need(type(name) is str and not name.startswith('/') and
             all(p not in ('', '.', '..') for p in name.split('/')), 'CAP_SOURCE_REJECTED')
        row, data = measure(root / name, 4 * 1024 * 1024, False)
        need(not row['aliases'] and row['nlink'] == 1 and not row['mode'] & 0o022 and
             row['sha256'] == entry['sha256'], 'CAP_SOURCE_REJECTED')
        result[name] = row
    need(result['recipe/jammy_metadata.py']['sha256'] == METADATA_SOURCE_SHA256, 'CAP_SOURCE_REJECTED')
    return result


def metadata_module(root):
    path = root / 'recipe/jammy_metadata.py'
    raw = measure(path, 4 * 1024 * 1024, False)[1]
    need(digest(raw) == METADATA_SOURCE_SHA256, 'CAP_SOURCE_REJECTED')
    module = types.ModuleType('capability_jammy_metadata')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def runtime_flags(root):
    prefix = sys.pycache_prefix
    need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and
         isinstance(prefix, str) and Path(prefix).is_absolute() and
         prefix == str(Path(root).absolute() / 'unused-pycache') and not os.path.lexists(prefix) and
         sys.path == PYTHON_PATHS and not os.path.lexists(PYTHON_PATHS[0]),
         'CAP_INTERPRETER_REJECTED')
    return prefix


def command(argv, out, label, limit=256 * 1024 * 1024):
    """Only the declared, read-only bootstrap programs may be invoked here."""
    allowed = (len(argv) == 3 and argv[0] == '/usr/bin/dpkg-query' and argv[1] == '--search' or
               len(argv) == 3 and argv[0] == '/usr/bin/dpkg-deb' and argv[1] in ('--field', '--fsys-tarfile') or
               len(argv) == 5 and argv[:3] == ['/usr/bin/gpgv', '--status-fd=1', '--keyring'] and
               argv[3] == '/usr/share/keyrings/ubuntu-archive-keyring.gpg')
    need(allowed and type(argv[-1]) is str and argv[-1].startswith('/') and
         re.fullmatch('[a-z0-9-]{1,64}', label), 'CAP_RUNTIME_UNSUPPORTED')
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'LANG': 'C', 'HOME': str(out)}
    result = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    need(len(result.stdout) <= limit and len(result.stderr) <= 1024 * 1024, 'CAP_IO_FAILED')
    with (out / (label + '.stderr')).open('xb') as stream:
        stream.write(result.stderr)
    return result.returncode, result.stdout


def load_metadata(root, m, out):
    directory = root / 'metadata' / ('snapshot-' + SNAPSHOT)
    directory.mkdir(parents=True, mode=0o700)
    records, evidence = {}, {}
    for suite, expected in m.RELEASE_HASHES.items():
        release = directory / (suite + '.InRelease')
        m.download_verified(m.ORIGIN + 'dists/' + suite + '/InRelease', release, m.RELEASE_SIZES[suite], expected)
        rc, result = command(['/usr/bin/gpgv', '--status-fd=1', '--keyring', str(m.KEYRING), str(release)], out, suite)
        need(rc == 0 and ('[GNUPG:] VALIDSIG ' + m.SIGNER + ' ').encode() in result, 'CAP_METADATA_REJECTED')
        payload = m.cleartext(release.read_text())
        header = m.fields(payload.split('MD5Sum:', 1)[0])
        need(header.get('Origin') == 'Ubuntu' and header.get('Suite') == suite and
             header.get('Codename') == 'jammy', 'CAP_METADATA_REJECTED')
        entries = m.hash_entries(payload)
        evidence[str(release.relative_to(root))] = measure(release, root_owned=False)[0]
        for component in ('main', 'universe'):
            index = directory / (suite + '.' + component + '.amd64.Packages.xz')
            relative = component + '/binary-amd64/Packages.xz'
            expected_hash, size = entries[relative]
            need(0 < size <= 16 * 1024 * 1024, 'CAP_METADATA_REJECTED')
            m.download_verified(m.ORIGIN + 'dists/' + suite + '/' + relative, index, size, expected_hash)
            evidence[str(index.relative_to(root))] = measure(index, root_owned=False)[0]
            for ordinal, row in enumerate(m.package_index_rows(index.read_bytes())):
                row.update(_suite=suite, _component=component, _stanza=ordinal)
                records.setdefault(m.package_identity(row), []).append(row)
    return records, evidence


def select_record(name, installed, records):
    matches = [value for value in installed.values() if value['name'] == name and value['architecture'] in ('amd64', 'all')]
    need(len(matches) == 1, 'CAP_PACKAGE_UNAUTHENTICATED')
    value = matches[0]
    rows = records.get((name, value['version'], value['architecture']), [])
    need(bool(rows), 'CAP_PACKAGE_UNAUTHENTICATED')
    row = rows[0]
    need(re.fullmatch('[a-z0-9][a-z0-9+.-]{1,59}', row['Package']) and
         re.fullmatch('[0-9][0-9A-Za-z.+:~-]{0,53}', row['Version']), 'CAP_METADATA_REJECTED')
    return row


def archive_members(data):
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        for member in archive:
            name = member.name.removeprefix('./')
            if name in ('', '.') or member.isdir():
                continue
            need(not name.startswith('/') and all(x not in ('', '.', '..') for x in name.split('/')) and
                 name not in result, 'CAP_ARCHIVE_REJECTED')
            if member.isfile():
                need(member.size <= 64 * 1024 * 1024, 'CAP_ARCHIVE_REJECTED')
                content = archive.extractfile(member).read()
                result[name] = {'kind': 'file', 'sha256': digest(content), 'size': member.size,
                                'mode': member.mode, 'uid': member.uid, 'gid': member.gid}
            elif member.issym():
                result[name] = {'kind': 'symlink', 'target': member.linkname}
            elif member.islnk():
                result[name] = {'kind': 'hardlink', 'target': member.linkname.removeprefix('./')}
            else:
                raise PreparationError('CAP_ARCHIVE_REJECTED')
    return result


def verify_member(row, members):
    candidates = [row['path'].lstrip('/'), row['resolved_path'].lstrip('/')]
    for value in list(candidates):
        if value.startswith(('usr/lib/', 'usr/lib64/', 'usr/bin/', 'usr/sbin/')):
            candidates.append(value[4:])
    selected = [members[value] for value in candidates if value in members and members[value]['kind'] == 'file']
    need(selected, 'CAP_BYTES_REJECTED')
    need(any(x['sha256'] == row['sha256'] and x['size'] == row['size'] and
             x['mode'] == row['mode'] and x['uid'] == row['uid'] and x['gid'] == row['gid'] for x in selected),
         'CAP_BYTES_REJECTED')
    for alias in row['aliases']:
        name = alias['path'].lstrip('/')
        if name in ('bin', 'sbin', 'lib', 'lib64'):
            need(alias['target'] == 'usr/' + name, 'CAP_BYTES_REJECTED')
        else:
            names = [name, name[4:] if name.startswith('usr/lib') else name]
            need(any(n in members and members[n]['kind'] == 'symlink' and
                     members[n]['target'] == alias['target'] for n in names), 'CAP_BYTES_REJECTED')


def cstring(data, offset, end=None):
    end = len(data) if end is None else min(len(data), end)
    need(0 <= offset < end, 'CAP_RUNTIME_UNSUPPORTED')
    stop = data.find(b'\0', offset, end)
    need(stop >= offset and stop - offset <= 4096, 'CAP_RUNTIME_UNSUPPORTED')
    return data[offset:stop].decode('ascii')


def elf_inputs(data):
    """Small data-only ELF64 little-endian x86-64 dependency reader."""
    need(len(data) >= 64 and data[:6] == b'\x7fELF\x02\x01' and
         struct.unpack_from('<H', data, 18)[0] == 62, 'CAP_RUNTIME_UNSUPPORTED')
    offset = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    need(size == 56 and 0 < count <= 128 and offset + size * count <= len(data), 'CAP_RUNTIME_UNSUPPORTED')
    loads, dynamic, interp = [], None, None
    for i in range(count):
        kind, flags, start, address, physical, length, memory, align = struct.unpack_from('<IIQQQQQQ', data, offset + i * size)
        need(start + length <= len(data), 'CAP_RUNTIME_UNSUPPORTED')
        if kind == 1:
            loads.append((address, start, length))
        elif kind == 2:
            need(dynamic is None and length <= 1024 * 1024, 'CAP_RUNTIME_UNSUPPORTED')
            dynamic = data[start:start + length]
        elif kind == 3:
            need(interp is None, 'CAP_RUNTIME_UNSUPPORTED')
            interp = cstring(data, start, start + length)
            need(interp == '/lib64/ld-linux-x86-64.so.2', 'CAP_RUNTIME_UNSUPPORTED')
    need(dynamic is not None and len(dynamic) % 16 == 0, 'CAP_RUNTIME_UNSUPPORTED')
    needed, table, table_size, terminated = [], None, None, False
    for i in range(0, len(dynamic), 16):
        tag, value = struct.unpack_from('<qQ', dynamic, i)
        if tag == 0:
            terminated = True
            break
        need(tag not in (15, 29, 0x6ffffefb, 0x6ffffefc, 0x7ffffffd, 0x7fffffff), 'CAP_RUNTIME_UNSUPPORTED')
        if tag == 1:
            needed.append(value)
        elif tag == 5:
            table = value
        elif tag == 10:
            table_size = value
    need(terminated and table is not None and table_size is not None and len(needed) <= 128, 'CAP_RUNTIME_UNSUPPORTED')
    positions = [(start + table - address, start + length) for address, start, length in loads
                 if address <= table and table + table_size <= address + length]
    need(len(positions) == 1, 'CAP_RUNTIME_UNSUPPORTED')
    start, end = positions[0]
    names = [cstring(data, start + value, start + table_size) for value in needed]
    need(all(re.fullmatch('[A-Za-z0-9_+.-]{1,128}', name) for name in names), 'CAP_RUNTIME_UNSUPPORTED')
    return interp, names


def loader_cache(data):
    need(len(data) >= 48 and data[:20] == b'glibc-ld.so.cache1.1' and data[28] & 3 in (0, 2), 'CAP_RUNTIME_UNSUPPORTED')
    count, strings = struct.unpack_from('<II', data, 20)
    start, end = 48 + count * 24, 48 + count * 24 + strings
    need(count <= 20000 and end <= len(data), 'CAP_RUNTIME_UNSUPPORTED')
    result = {}
    for i in range(count):
        flags, key, value, version, hwcap = struct.unpack_from('<iIIIQ', data, 48 + i * 24)
        if flags != 0x303:
            continue
        need(start <= key < end and start <= value < end, 'CAP_RUNTIME_UNSUPPORTED')
        name, path = cstring(data, key, end), cstring(data, value, end)
        need(path.startswith('/') and '..' not in Path(path).parts, 'CAP_RUNTIME_UNSUPPORTED')
        result.setdefault(name, set()).add(path)
    return result


class Authenticator:
    def __init__(self, root, m, out, installed, records):
        self.root, self.m, self.out = root, m, out
        self.installed, self.records = installed, records
        self.packages, self.members, self.files = {}, {}, {}
        self.serial = 0

    def package(self, name):
        if name in self.members:
            return self.members[name]
        need(len(self.members) < 96, 'CAP_RUNTIME_UNSUPPORTED')
        row = select_record(name, self.installed, self.records)
        need(0 < int(row['Size']) <= 64 * 1024 * 1024, 'CAP_ARCHIVE_REJECTED')
        archive = self.out / (str(len(self.members)) + '.deb')
        self.m.download_payload(row, archive)
        rc, control = command(['/usr/bin/dpkg-deb', '--field', str(archive)], self.out, 'control-' + str(len(self.members)))
        parsed = self.m.fields(control.decode())
        need(rc == 0 and self.m.package_identity(parsed) == self.m.package_identity(row), 'CAP_ARCHIVE_REJECTED')
        rc, data = command(['/usr/bin/dpkg-deb', '--fsys-tarfile', str(archive)], self.out, 'data-' + str(len(self.members)))
        need(rc == 0, 'CAP_ARCHIVE_REJECTED')
        self.members[name] = archive_members(data)
        self.packages[name] = {'name': row['Package'], 'version': row['Version'],
            'architecture': row['Architecture'], 'suite': row['_suite'], 'component': row['_component'],
            'stanza': row['_stanza'], 'archive': measure(archive, root_owned=False)[0]}
        return self.members[name]

    def owner(self, path):
        candidates = [path]
        if path.startswith(('/usr/lib/', '/usr/lib64/', '/usr/bin/', '/usr/sbin/')):
            candidates.append(path[4:])
        elif path.startswith(('/lib/', '/lib64/', '/bin/', '/sbin/')):
            candidates.append('/usr' + path)
        owners = set()
        for candidate in candidates:
            self.serial += 1
            rc, output = command(['/usr/bin/dpkg-query', '--search', candidate], self.out, 'owner-' + str(self.serial), 65536)
            if rc == 1:
                need(not output, 'CAP_OWNER_REJECTED')
                continue
            need(rc == 0, 'CAP_OWNER_REJECTED')
            for line in output.decode().splitlines():
                match = re.fullmatch(r'([a-z0-9][a-z0-9+.-]*)(?::amd64|:all)?: (.*)', line)
                need(match and match[2] == candidate, 'CAP_OWNER_REJECTED')
                owners.add(match[1])
        need(len(owners) == 1, 'CAP_OWNER_REJECTED')
        return next(iter(owners))

    def authenticate(self, path, expected=None, archive_owner=None):
        if path in self.files:
            return self.files[path]
        row, data = measure(path)
        owner = archive_owner if archive_owner is not None else self.owner(path)
        need(expected is None or owner == expected, 'CAP_OWNER_REJECTED')
        verify_member(row, self.package(owner))
        row['package'] = owner
        self.files[path] = row
        return row


def library_paths(name, cache):
    paths = set(cache.get(name, ()))
    for directory in LIBDIRS:
        path = Path(directory) / name
        if path.exists():
            paths.add(str(path))
        base = Path(directory)
        for legacy in ('tls', 'haswell', 'x86_64', 'avx512_1'):
            need(not (base / legacy).exists(), 'CAP_RUNTIME_UNSUPPORTED')
        if (base / 'glibc-hwcaps').exists():
            for path in (base / 'glibc-hwcaps').glob('*/' + name):
                paths.add(str(path))
    need(paths and len(paths) <= 32, 'CAP_RUNTIME_UNSUPPORTED')
    return sorted(paths)


def loginuid_value():
    # glibc 2.35 Linux getlogin_r: malformed input returns -1 and enables tty
    # fallback, but UINT32_MAX returns positive ENXIO before any NSS lookup.
    with Path('/proc/self/loginuid').open('rb') as stream:
        raw = stream.read(12)
    need(re.fullmatch(b'(0|[1-9][0-9]{0,9})', raw) and int(raw) <= 4294967295,
         'CAP_LOGINUID_UNSUPPORTED')
    return raw.decode('ascii')


def nss_providers(text):
    databases = {}
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        need(':' in line, 'CAP_NSS_UNSUPPORTED')
        name, body = line.split(':', 1)
        name = name.strip()
        need(name not in databases, 'CAP_NSS_UNSUPPORTED')
        databases[name] = body.split()
    providers = {name: databases.get(name) for name in ('passwd', 'group')}
    need(all(value in (['files'], ['files', 'systemd']) for value in providers.values()) and
         ('subid' not in databases or databases['subid'] == ['files']), 'CAP_NSS_UNSUPPORTED')
    return providers


def nss_candidates(name, cache):
    # Enumerate both the generic NSS soname and Ubuntu's fixed glibc-2.35
    # local-nss-upgrade retry, including missing paths. No RPATH exemption.
    paths, absent = set(cache.get(name, ())), set()
    for directory in LIBDIRS:
        base = Path(directory)
        for legacy in ('tls', 'haswell', 'x86_64', 'avx512_1'):
            need(not (base / legacy).exists(), 'CAP_RUNTIME_UNSUPPORTED')
        candidates = [base / name]
        if (base / 'glibc-hwcaps').exists():
            candidates.extend(path / name for path in (base / 'glibc-hwcaps').glob('*') if path.is_dir())
        for path in candidates:
            if os.path.lexists(path):
                paths.add(str(path))
            else:
                absent.add(str(path))
    need(len(paths) <= 32 and len(absent) <= 128, 'CAP_RUNTIME_UNSUPPORTED')
    return paths, absent - paths


def nss_inputs(text, cache):
    providers = nss_providers(text)
    paths, absent = set(), set()
    if any('systemd' in value for value in providers.values()):
        for index, name in enumerate(NSS_SONAMES):
            found, missing = nss_candidates(name, cache)
            if index == 0:
                need(found, 'CAP_NSS_PROVIDER_UNAUTHENTICATED')
            paths.update(found)
            absent.update(missing)
    return {'providers': providers, 'fallback_paths': sorted(paths), 'absent_paths': sorted(absent)}


def authenticate_nss(auth, nss):
    try:
        for path in nss['fallback_paths']:
            auth.authenticate(path, 'libnss-systemd')
    except (PreparationError, OSError):
        raise PreparationError('CAP_NSS_PROVIDER_UNAUTHENTICATED') from None


def check_nss_state(lock, cache):
    need(nss_inputs(Path('/etc/nsswitch.conf').read_text(), cache) == lock['nss'], 'CAP_STATE_CHANGED')
    need(all(path in lock['runtime_files'] and path in lock['runtime_elf_paths'] and
             lock['runtime_files'][path].get('package') == 'libnss-systemd'
             for path in lock['nss']['fallback_paths']), 'CAP_LOCK_REJECTED')


def runtime_closure(auth, initial, cache):
    queue, seen = list(initial), set()
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        need(len(seen) < 512, 'CAP_RUNTIME_UNSUPPORTED')
        seen.add(path)
        auth.authenticate(path)
        row, data = measure(path)
        interp, needed = elf_inputs(data)
        if interp:
            queue.append(interp)
        for name in needed:
            queue.extend(library_paths(name, cache))
    return sorted(seen)


def python_files():
    base = Path('/usr/lib/python3.10')
    need(base.is_dir(), 'CAP_INTERPRETER_REJECTED')
    files = []
    for path in base.rglob('*'):
        need(not (path.is_symlink() and path.is_dir()), 'CAP_RUNTIME_UNAUTHENTICATED')
        if path.suffix == '.pyc' and '__pycache__' not in path.parts:
            raise PreparationError('CAP_RUNTIME_UNAUTHENTICATED')
        if path.suffix in ('.py', '.so'):
            files.append(str(path))
    need(100 <= len(files) <= 10000, 'CAP_INTERPRETER_REJECTED')
    return sorted(files)


def authenticate_python(auth, paths):
    for package in PYTHON_PACKAGES:
        auth.package(package)
    for path in paths:
        owners = [package for package in PYTHON_PACKAGES if path.lstrip('/') in auth.members[package]]
        if not owners:
            # Development/test files are not silently skipped: their exact installed
            # identity and same python3.10 source must also be in the signed snapshot.
            owner = auth.owner(path)
            need(owner in PYTHON_OPTIONAL_PACKAGES, 'CAP_RUNTIME_UNAUTHENTICATED')
            row = select_record(owner, auth.installed, auth.records)
            need(row.get('Source', owner).split()[0] == PYTHON_OPTIONAL_PACKAGES[owner], 'CAP_RUNTIME_UNAUTHENTICATED')
            auth.package(owner)
            owners = [owner]
        need(len(owners) == 1, 'CAP_RUNTIME_UNAUTHENTICATED')
        auth.authenticate(path, archive_owner=owners[0])


def verify_interpreter(row):
    """A held executable FD is fine; a copied or different interpreter is not."""
    current = os.stat('/proc/self/exe')
    need(sys.version_info[:2] == (3, 10) and
         (current.st_dev, current.st_ino, current.st_size) ==
         (row['device'], row['inode'], row['size']) and
         digest(Path('/proc/self/exe').read_bytes()) == row['sha256'], 'CAP_INTERPRETER_REJECTED')


def check_runtime_paths(initial, cache, expected):
    queue, seen = list(initial), set()
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        need(path in expected and len(seen) < 512, 'CAP_STATE_CHANGED')
        seen.add(path)
        interp, names = elf_inputs(measure(path)[1])
        if interp:
            queue.append(interp)
        for name in names:
            queue.extend(library_paths(name, cache))
    need(seen == set(expected), 'CAP_STATE_CHANGED')


def write_new(path, value):
    data = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
    partial = path.with_name(path.name + '.partial')
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    os.link(partial, path, follow_symlinks=False)
    partial.unlink()


def authenticate_tools(auth):
    tools = {}
    for name, path in TOOLS.items():
        try:
            tools[name] = auth.authenticate(path, TOOL_PACKAGES[name])
            need(tools[name]['mode'] & 0o111, 'CAP_MODE_REJECTED')
            if name in ('newuidmap', 'newgidmap'):
                need(tools[name]['mode'] & stat.S_ISUID and tools[name]['uid'] == 0, 'CAP_MODE_REJECTED')
        except PreparationError as error:
            code = 'CAP_' + name.upper() + '_' + error.code.removeprefix('CAP_')
            raise PreparationError(code if code in PREPARATION_CODES else error.code) from None
    return tools


def prepare(root, expected):
    root = Path(root).absolute()
    source_files = source_anchor(root, expected)
    need(platform.machine() == 'x86_64' and sys.version_info[:2] == (3, 10) and
         sys.executable == TOOLS['python'], 'CAP_HOST_UNSUPPORTED')
    prefix = runtime_flags(root)
    m = metadata_module(root)
    release = m.os_values(Path('/usr/lib/os-release').read_text())
    need(release.get('ID') == 'ubuntu' and release.get('VERSION_ID') == '22.04', 'CAP_HOST_UNSUPPORTED')
    need(os.geteuid() == os.getuid() != 0 and os.getegid() == os.getgid(), 'CAP_HOST_UNSUPPORTED')
    for name, path in TOOLS.items():
        need(Path(path).is_file(), 'CAP_' + name.upper() + '_MISSING')
    need(not (root / 'capability-inputs.lock.json').exists(), 'CAP_LOCK_REJECTED')
    out = root / 'capability-input-evidence'
    out.mkdir(mode=0o700)
    host_files = {path: measure(path)[0] for path in HOST_FILES}
    need(not os.path.lexists(NSCD_SOCKET), 'CAP_NSCD_PRESENT')
    absent = [PYTHON_PATHS[0], NSCD_SOCKET]
    for path in OPTIONAL_HOST_FILES:
        if os.path.lexists(path):
            host_files[path] = measure(path)[0]
        else:
            absent.append(path)
    if os.path.lexists('/etc/ld.so.preload'):
        row, data = measure('/etc/ld.so.preload', 65536)
        need(not any(line.split(b'#', 1)[0].strip() for line in data.splitlines()), 'CAP_CONFIGURATION_REJECTED')
        host_files['/etc/ld.so.preload'] = row
    else:
        absent.append('/etc/ld.so.preload')
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    need(re.fullmatch('[0-9a-f-]{36}', boot_id), 'CAP_HOST_UNSUPPORTED')
    host = {'uid': os.getuid(), 'gid': os.getgid(), 'groups': sorted(os.getgroups()),
            'boot_id': boot_id, 'pycache_prefix': prefix, 'python_path': list(sys.path),
            'loginuid': loginuid_value()}
    try:
        records, metadata_files = load_metadata(root, m, out)
    except PreparationError:
        raise
    except Exception:
        raise PreparationError('CAP_METADATA_REJECTED') from None
    installed = m.inventory(Path('/var/lib/dpkg/status').read_text())
    auth = Authenticator(root, m, out, installed, records)
    tools = authenticate_tools(auth)
    stdlib = python_files()
    authenticate_python(auth, stdlib)
    bootstrap = {name: auth.authenticate(path) for name, path in BOOTSTRAP_TOOLS.items()}
    auth.authenticate('/usr/share/keyrings/ubuntu-archive-keyring.gpg', 'ubuntu-keyring')
    initial = list(TOOLS.values()) + list(BOOTSTRAP_TOOLS.values()) + [path for path in stdlib if path.endswith('.so')]
    cache = loader_cache(Path('/etc/ld.so.cache').read_bytes())
    nss = nss_inputs(Path('/etc/nsswitch.conf').read_text(), cache)
    authenticate_nss(auth, nss)
    initial.extend(nss['fallback_paths'])
    runtime = runtime_closure(auth, initial, cache)
    lock = {'schema': 1, 'status': 'authenticated-existing-tools', 'scope': 'namespace-capability-only',
        'source_index_sha256': expected, 'snapshot': SNAPSHOT, 'host': host, 'tools': tools,
        'host_files': host_files, 'source_files': source_files, 'runtime_files': auth.files,
        'bootstrap_files': bootstrap, 'nss': nss,
        'runtime_elf_paths': runtime, 'python_source_paths': stdlib, 'absent_paths': absent,
        'metadata_files': metadata_files, 'packages': auth.packages,
        'bootstrap_trust': 'initial-system-python-and-read-only-dpkg-gpgv-dpkg-deb'}
    verify_state(root, lock)
    write_new(root / 'capability-inputs.lock.json', lock)
    return lock


def verify_state(root, lock):
    need(type(lock.get('schema')) is int and lock.get('schema') == 1 and lock.get('status') == 'authenticated-existing-tools' and
         lock.get('scope') == 'namespace-capability-only' and lock.get('snapshot') == SNAPSHOT,
         'CAP_LOCK_REJECTED')
    need(set(lock['tools']) == set(TOOLS) and all(lock['tools'][name]['path'] == path for name, path in TOOLS.items()), 'CAP_LOCK_REJECTED')
    need(set(lock['bootstrap_files']) == set(BOOTSTRAP_TOOLS) and
         all(lock['bootstrap_files'][name]['path'] == path for name, path in BOOTSTRAP_TOOLS.items()), 'CAP_LOCK_REJECTED')
    optional = set(OPTIONAL_HOST_FILES) | {'/etc/ld.so.preload'}
    need(set(HOST_FILES).issubset(lock['host_files']) and
         set(lock['host_files']).issubset(set(HOST_FILES) | optional) and
         set(lock['absent_paths']).issubset(optional | {PYTHON_PATHS[0], NSCD_SOCKET}) and
         len(lock['absent_paths']) == len(set(lock['absent_paths'])) and
         not (set(lock['host_files']) & set(lock['absent_paths'])) and
         optional.issubset(set(lock['host_files']) | set(lock['absent_paths'])), 'CAP_LOCK_REJECTED')
    need(lock['host']['python_path'] == PYTHON_PATHS and
         {PYTHON_PATHS[0], NSCD_SOCKET}.issubset(lock['absent_paths']), 'CAP_LOCK_REJECTED')
    need(not os.path.lexists(NSCD_SOCKET), 'CAP_NSCD_PRESENT')
    need(loginuid_value() == lock['host']['loginuid'], 'CAP_STATE_CHANGED')
    verify_interpreter(lock['tools']['python'])
    need(runtime_flags(root) == lock['host']['pycache_prefix'], 'CAP_STATE_CHANGED')
    need((os.getuid(), os.getgid(), sorted(os.getgroups())) ==
         (lock['host']['uid'], lock['host']['gid'], lock['host']['groups']) and
         Path('/proc/sys/kernel/random/boot_id').read_text().strip() == lock['host']['boot_id'], 'CAP_STATE_CHANGED')
    need(source_anchor(root, lock['source_index_sha256']) == lock['source_files'], 'CAP_SOURCE_REJECTED')
    for mapping, root_owned in ((lock['tools'], True), (lock['bootstrap_files'], True), (lock['runtime_files'], True),
                                (lock['host_files'], True), (lock['metadata_files'], False)):
        for row in mapping.values():
            measured, unused = measure(row['path'], root_owned=root_owned)
            need(measured == {k: row[k] for k in FILE_KEYS}, 'CAP_STATE_CHANGED')
    for package in lock['packages'].values():
        row = package['archive']
        need(measure(row['path'], root_owned=False)[0] == row, 'CAP_STATE_CHANGED')
    need(all(not os.path.lexists(path) for path in lock['absent_paths']) and
         python_files() == lock['python_source_paths'], 'CAP_STATE_CHANGED')
    initial = list(TOOLS.values()) + list(BOOTSTRAP_TOOLS.values()) + [path for path in lock['python_source_paths'] if path.endswith('.so')]
    cache = loader_cache(Path('/etc/ld.so.cache').read_bytes())
    check_nss_state(lock, cache)
    initial.extend(lock['nss']['fallback_paths'])
    check_runtime_paths(initial, cache, lock['runtime_elf_paths'])


def verify_lock(root, expected_lock_sha256):
    root = Path(root).absolute()
    need(re.fullmatch('[0-9a-f]{64}', expected_lock_sha256 or ''), 'CAP_LOCK_REJECTED')
    row, raw = measure(root / 'capability-inputs.lock.json', 16 * 1024 * 1024, False)
    need(not row['aliases'] and row['nlink'] == 1 and row['mode'] == 0o600 and
         digest(raw) == expected_lock_sha256, 'CAP_LOCK_REJECTED')
    lock = unique_json(raw)
    verify_state(root, lock)
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--expected-source-index-sha256', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepare(args.root, args.expected_source_index_sha256)
        status = {'schema': 1, 'status': 'PASS', 'code': 'CAP_INPUTS_VERIFIED'}
    except PreparationError as error:
        status = {'schema': 1, 'status': 'FAIL', 'code': error.code}
    except OSError:
        status = {'schema': 1, 'status': 'FAIL', 'code': 'CAP_IO_FAILED'}
    except Exception:
        status = {'schema': 1, 'status': 'FAIL', 'code': 'CAP_UNEXPECTED_ERROR'}
    try:
        write_new(args.root / 'capability-preparation-status.json', status)
    except OSError:
        status = {'schema': 1, 'status': 'FAIL', 'code': 'CAP_IO_FAILED'}
    print(json.dumps(status, sort_keys=True, separators=(',', ':')))
    return 0 if status['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
