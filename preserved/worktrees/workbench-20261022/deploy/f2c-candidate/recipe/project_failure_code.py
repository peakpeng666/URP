#!/usr/bin/env python3
"""Read-only, bounded projection to fixed public failure codes. Never echo logs.

Invoke only after this self-contained helper's source anchor is verified. This
is a diagnostic hint, not an acceptance decision or a replacement exit status.
The CLI always emits one allowlisted token and exits zero, including on misuse.
"""
import os
import re
import stat
import sys

MAX_READ_BYTES = 64 * 1024
STAGES = frozenset({'helper_tests', 'packages', 'validation_inputs', 'measured_lock', 'offline_build', 'native_validation'})
# Tuples contain a fixed code, exact static error messages, and explicitly known
# static prefixes for helper errors that append private detail. That detail is
# NEVER extracted, interpolated, parsed as JSON, or returned to the caller.
PACKAGE_RULES = (
    ('APT_HOST_MISMATCH', ('Run only on native Ubuntu 22.04; no Debian or other-release preparation',
                           'Requires native amd64 runner', 'Wrong signed distribution'), ()),
    ('APT_SIGNATURE_REJECTED', ('Unexpected Ubuntu release signer', 'Not an InRelease',
                               'Release lacks SHA256', 'Signed package-index mismatch',
                               'Trusted Ubuntu keyring is missing; no bootstrap installation attempted'),
     ('Pinned InRelease changed: ', 'jammy-signature failed; see ', 'jammy-updates-signature failed; see ', 'jammy-security-signature failed; see ')),
    ('APT_ARCHIVE_MISMATCH', ('Existing artifact differs from authenticated hash/size',
                             'Artifact exceeds authenticated size', 'Archive control identity mismatch',
                             'Cached payload copy mismatch', 'APT URI size disagrees with signed metadata',
                             'APT URI differs from authenticated transaction archive'),
     ('Artifact hash/size mismatch: ', 'Archive redirected; stop for review: ')),
    ('APT_SOLVER_BLOCKED', ('Native APT resolver left broken packages', 'Native solved state has an unsatisfied dependency group',
                           'Solver changed exact root version', 'Native closure did not converge',
                           'Verified-payload APT transaction differs from native solution'),
     ('Exact root version unavailable in native cache: ', 'No authenticated Jammy archive for relevant dependency: ',
      'Cannot close pinned dependency provenance: ')),
    ('APT_PROVIDER_CONFLICT', ('Both pkgconf and pkg-config are installed; refuse destructive repair',
                              'Installed pkgconf is absent from authenticated snapshot; stop instead of remove',
                              'Installed pkgconf does not authentically provide pkg-config',
                              'Provider archive lacks pkg-config executable',
                              'Installed pkg-config alias differs from authenticated provider archive',
                              'Provider executable is not a regular package-owned file',
                              'Installed pkg-config executable differs from authenticated archive',
                              'Provider symlink target missing from archive', 'Unexpected provider link layout',
                              'Provider executable missing'), ()),
    ('APT_REMOVAL_REFUSED', ('Removal/downgrade/reinstall transaction refused', 'APT simulation proposes removal',
                            'Transaction changes held package'),
     ('Native APT proposes removal: ', 'Native APT proposes downgrade: ', 'Snapshot would downgrade a relevant installed package: ')),
    ('APT_INPUT_CHANGED', ('Package database changed during preparation', 'Package database changed before installation',
                          'Unexpected installed inventory change; no readiness lock emitted', 'Base version changed'),
     ('Post-install closure mismatch: ',)),
)
INDEX_RULE = ('GUARD_INDEX_MISMATCH', ('Artifact index anchor mismatch', 'artifact index anchor mismatch',
                                     'Helper anchor mismatch', 'Incomplete index', 'incomplete reviewed index',
                                     'Missing indexed helper/lock', 'Validation config anchor mismatch',
                                     'Reviewed source index anchor mismatch'),
              ('Indexed artifact mismatch: ', 'indexed artifact mismatch: ', 'Reviewed source input changed: '))
NETWORK_RULE = ('GUARD_NAMESPACE_REJECTED', ('Kernel boot changed; re-prepare and review baseline',
                                           'Not isolated from reviewed original host namespace',
                                           'Not isolated from PID1 network namespace', 'Unexpected network interfaces',
                                           'Loopback is UP; require pristine unshare namespace', 'Unexpected IPv4 route',
                                           'Unexpected IPv6 route', 'Inherited socket descriptor'), ())
INPUT_RULE = ('GUARD_INPUT_MISMATCH', ('Jammy preparation incomplete', 'Missing/duplicate closure scope',
                                     'Empty/unprepared tree lock', 'Incomplete package closure',
                                     'Package provenance covers only transaction delta', 'Changed F2C source identity',
                                     'Wrong OR-Tools runtime wheel', 'Extracted provider wheel differs',
                                     'Wrong Ubuntu22.04 interface archive'),
              ('Tree membership/content changed: ', 'Changed locked file: ', 'Missing locked file: ',
               'Changed file alias: ', 'Changed file resolution: ', 'Installed package version differs: '))
OUTPUT_RULE = ('GUARD_OUTPUT_EXISTS', ('Output already exists; select a separately reviewed fresh candidate root',
                                      'Never reuse validation output'), ())
PREPARATION_RULES = (
    ('PREPARATION_HOST_MISMATCH', ('Preparation requires exactly CPython 3.12.13',
                                  'Unexpected preparation interpreter/platform', 'Preparation requires actual Ubuntu22.04',
                                  'Interpreter patch version differs', 'Actual host is not Jammy'), ()),
    ('PREPARATION_INPUT_INCOMPLETE', ('Package preparation did not verify installation',
                                     'Package authentication/closure incomplete',
                                     'Package lock is transaction-only, not complete relevant dependency closure',
                                     'Missing official package byte provenance for selected command/provider'), ()),
    ('PREPARATION_ARCHIVE_REJECTED', ('Downloaded source hash/size mismatch', 'Existing download differs',
                                     'Nonregular source member', 'Duplicate archive member', 'Duplicate ZIP member',
                                     'ZIP alias/special file refused', 'Unbounded archive extraction',
                                     'Unbounded wheel extraction', 'Installed command/provider differs from official package bytes'), ()),
    ('PREPARATION_PROVIDER_REJECTED', ('OR-Tools interface definitions changed', 'OR-Tools compile options changed',
                                      'Protobuf propagated DLL definitions changed', 'GLIBC floor exceeds Jammy',
                                      'Missing actual Jammy system zlib alternative', 'Missing link-time wheel zlib selection'),
     ('Unresolved ELF dependency: ', 'ELF symbol-version requirement unsatisfied: ',
      'Zlib alternative lacks required symbol versions: ', 'Zlib alternative expands unmeasured dependency closure: ')),
)
VALIDATION_RULES = (
    ('VALIDATION_ABI_REJECTED', ('F2C RUNPATH is not the exact relative wheel layout',
                                'Not a Jammy system ABI candidate', 'Unreviewed loader path',
                                'Loader path leaves approved runtime roots', 'Absolute/path DT_NEEDED rejected'),
     ('Unresolved ELF dependency: ', 'Missing ELF symbol versions: ', 'Unresolved strong dynamic symbols: ',
      'libz alternate lacks required strong/versioned symbol: ')),
    ('VALIDATION_PROVIDER_REJECTED', ('Only libz alternate providers are allowed', 'Unknown libz policy',
                                     'Wrong wheel libz location', 'libz provider path alias', 'libz provider bytes changed',
                                     'Alternative is not libz.so.1', 'Unapproved alternate libz provider',
                                     'Multiple/wrong mapped libz providers', 'Multiple/wrong mapped OR-Tools providers',
                                     'Wrong static OR-Tools provider', 'Mapped provider drift', 'Mapped extension differs',
                                     'Measured system provider drift', 'System libz changed', 'Validation wheel libz differs'),
     ('Competing SONAME provider: ',)),
    ('VALIDATION_TEST_GATE_FAILED', ('Test count/failure/skip mismatch', 'Point roundtrip failed'),
     ('Native validation stage failed: ',)),
    ('VALIDATION_INTEGRITY_FAILED', ('Harness changed', 'Tool changed', 'Candidate wheel changed',
                                    'Historical wheel prohibited', 'Historical manifest changed',
                                    'Installed dependency/wheel tree drift', 'Wrong installed extension',
                                    'Final integrity failed', 'Source must be exact clean application185 checkout',
                                    'New wheel differs from build result', 'Extension differs from build result'),
     ('Input membership/content drift: ', 'Base-interpreter build closure failed: ')),
)
DATA_RULES = (
    ('VALIDATION_INPUT_REJECTED', ('Input size mismatch', 'Input SHA256 mismatch', 'Wrong application source revision',
                                  'Wrong uv version', 'Wrong Python version', 'Unexpected dependency startup hook',
                                  'Historical or unexpected Fields2Cover prohibited', 'Dependency symlink escapes tree',
                                  'Official map hash mismatch', 'Official dataset hash mismatch'), ()),
)
RULES = {
    'helper_tests': (),
    'packages': PACKAGE_RULES,
    'validation_inputs': DATA_RULES,
    'measured_lock': (INDEX_RULE, INPUT_RULE) + PREPARATION_RULES,
    'offline_build': (NETWORK_RULE, INDEX_RULE, INPUT_RULE, OUTPUT_RULE,
                      ('BUILD_STAGE_FAILED', ('Insufficient free disk', 'Expected exactly one new wheel',
                                              'New extension layout differs; re-review relative RPATH'),
                       ('Offline stage failed: ',))),
    'native_validation': (NETWORK_RULE, INDEX_RULE, INPUT_RULE, OUTPUT_RULE) + VALIDATION_RULES + DATA_RULES,
}
ALLOWED_CODES = frozenset({'UNKNOWN', 'HELPER_TESTS_FAILED'} | {code for rules in RULES.values() for code, _, _ in rules})
ERROR_PREFIXES = ('BLOCKED: ', 'Refusing: ', 'Preparation refused: ', 'RuntimeError: ', 'AssertionError: ')
UNSHARE_ERRORS = frozenset({'unshare: unshare failed: Operation not permitted',
                            'unshare: unshare failed: Invalid argument',
                            'unshare: unshare failed: Function not implemented'})

def safe_tail(path):
    """Open every component without following symlinks; never block on a FIFO."""
    directories, fd = [], None
    try:
        if not isinstance(path, str) or not path or '\x00' in path:
            return None
        absolute = path.startswith('/')
        parts = path.split('/')[1:] if absolute else path.split('/')
        if not parts or len(parts) > 128 or any(part in ('', '.', '..') for part in parts):
            return None
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory = os.open('/' if absolute else '.', directory_flags)
        directories.append(directory)
        for part in parts[:-1]:
            directory = os.open(part, directory_flags, dir_fd=directory)
            directories.append(directory)
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            return None
        offset = max(0, before.st_size - MAX_READ_BYTES)
        data = os.pread(fd, min(before.st_size, MAX_READ_BYTES), offset)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != \
           (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            return None
        if offset:
            # A bounded tail may start in the middle of a line or UTF-8 codepoint.
            # Discard that partial record instead of accidentally matching it.
            newline = data.find(b'\n')
            if newline < 0:
                return None
            data = data[newline + 1:]
        text = data.decode('utf-8', errors='strict').replace('\r\n', '\n')
        if any(ord(char) < 32 and char not in '\n\t' or ord(char) == 127 for char in text):
            return None
        return text
    except Exception:
        return None
    finally:
        for descriptor in ([fd] if fd is not None else []) + list(reversed(directories)):
            try:
                os.close(descriptor)
            except OSError:
                pass

def project(stage, log_path):
    if stage not in STAGES:
        return 'UNKNOWN'
    text = safe_tail(log_path)
    if text is None:
        return 'UNKNOWN'
    for line in reversed(text.splitlines()):
        if stage == 'helper_tests' and re.fullmatch(r'FAILED \((?:failures|errors)=[0-9]+(?:, (?:failures|errors|skipped)=[0-9]+)*\)', line):
            return 'HELPER_TESTS_FAILED'
        if line in UNSHARE_ERRORS and stage in ('offline_build', 'native_validation'):
            return 'GUARD_NAMESPACE_REJECTED'
        for prefix in ERROR_PREFIXES:
            if line.startswith(prefix):
                message = line[len(prefix):]
                for code, exact, known_prefixes in RULES[stage]:
                    if message in exact or any(message.startswith(pattern) and len(message) > len(pattern) for pattern in known_prefixes):
                        return code
                # Never fall back to an earlier recognized failure after an
                # unrecognized terminal error record.
                return 'UNKNOWN'
    return 'UNKNOWN'

def main(argv=None):
    code = 'UNKNOWN'
    try:
        argv = sys.argv[1:] if argv is None else argv
        if len(argv) == 4 and argv[0] in ('--stage', '--log') and argv[2] in ('--stage', '--log') and argv[0] != argv[2]:
            options = {argv[0]: argv[1], argv[2]: argv[3]}
            code = project(options['--stage'], options['--log'])
        if code not in ALLOWED_CODES:
            code = 'UNKNOWN'
    except Exception:
        code = 'UNKNOWN'
    try:
        os.write(1, (code + '\n').encode('ascii'))
    except OSError:
        pass
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
