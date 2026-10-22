"""Stdlib fixtures only. Never invoke APT, install packages, or download payloads."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import types
import unittest
from unittest import mock
import hashlib
import sys

SCRIPT = Path(__file__).resolve().parents[1] / 'prepare_jammy_packages.py'
spec = importlib.util.spec_from_file_location('prepare_jammy_packages', SCRIPT)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def row(name='a', version='1', arch='amd64', held=False):
    return {'name': name, 'version': version, 'architecture': arch, 'held': held}


def control(name='a', version='1', arch='amd64', status='install ok installed'):
    return f'Package: {name}\nVersion: {version}\nArchitecture: {arch}\nStatus: {status}\n'


def version(identifier, name, ver='1', dependencies=None):
    pkg = types.SimpleNamespace(id=identifier, name=name)
    return types.SimpleNamespace(parent_pkg=pkg, ver_str=ver, arch='amd64', depends_list=dependencies or {})


def dep(*versions):
    return types.SimpleNamespace(all_targets=lambda: list(versions))


class TestHostAndMetadata(unittest.TestCase):
    def test_host_jammy(self):
        p.check_host({'ID': 'ubuntu', 'VERSION_ID': '22.04'}, 'x86_64', 'amd64')

    def test_wrong_distribution(self):
        for release in ({'ID': 'debian', 'VERSION_ID': '13'}, {'ID': 'ubuntu', 'VERSION_ID': '24.04'}):
            with self.assertRaises(RuntimeError):
                p.check_host(release, 'x86_64', 'amd64')

    def test_wrong_architecture(self):
        with self.assertRaises(RuntimeError):
            p.check_host({'ID': 'ubuntu', 'VERSION_ID': '22.04'}, 'aarch64', 'arm64')

    def test_os_release_not_executed(self):
        self.assertEqual(p.os_values('ID="ubuntu"\nVERSION_ID="22.04"\n'), {'ID': 'ubuntu', 'VERSION_ID': '22.04'})

    def test_control_continuations(self):
        self.assertEqual(p.fields('Depends: a,\n b\nVersion: 1\n')['Depends'], 'a,\n b')

    def test_duplicate_fields_rejected(self):
        with self.assertRaises(RuntimeError):
            p.fields('Version: 1\nVersion: 2\n')

    def test_cleartext_dash_escape(self):
        text = '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\nOrigin: Ubuntu\n- -field\n-----BEGIN PGP SIGNATURE-----\nabc'
        self.assertEqual(p.cleartext(text), 'Origin: Ubuntu\n-field\n')

    def test_hash_entries(self):
        h = 'a' * 64
        self.assertEqual(p.hash_entries('SHA256:\n ' + h + ' 3 main/Packages\nSHA512:\n'), {'main/Packages': (h, 3)})

    def test_duplicate_hash_entries(self):
        entry = ' ' + 'a' * 64 + ' 3 main/Packages\n'
        with self.assertRaises(RuntimeError):
            p.hash_entries('SHA256:\n' + entry + entry)

    def test_safe_archive_paths(self):
        good = 'pool/main/a/abc/abc_1.0+dfsg-1_amd64.deb'
        self.assertEqual(p.safe_archive_path(good), good)
        for bad in ('https://bad/x.deb', '/pool/x.deb', 'pool/../x.deb', 'pool/a%2fb.deb',
                    'pool/a?x.deb', 'pool/a\\b.deb', 'pool/a b.deb', 'pool/a.txt'):
            with self.subTest(bad=bad), self.assertRaises(RuntimeError):
                p.safe_archive_path(bad)


class TestProvidersAndInventory(unittest.TestCase):
    def test_inventory_only_installed(self):
        status = control() + '\n' + control('old', status='deinstall ok config-files') + '\n' + control('held', status='hold ok installed')
        self.assertEqual(set(p.inventory(status)), {'a:amd64', 'held:amd64'})
        self.assertTrue(p.inventory(status)['held:amd64']['held'])

    def test_default_root_is_exact_pkg_config(self):
        roots, providers = p.choose_roots({}, {})
        self.assertEqual(roots['pkg-config'], '0.29.2-1ubuntu3')
        self.assertFalse(providers)

    def test_keep_authenticated_pkgconf(self):
        installed = {'pkgconf:amd64': row('pkgconf', '1.8.0-1')}
        records = {('pkgconf', '1.8.0-1', 'amd64'): [{'Provides': 'pkg-config (= 0.29-1)'}]}
        roots, providers = p.choose_roots(installed, records)
        self.assertNotIn('pkg-config', roots)
        self.assertEqual(roots['pkgconf'], '1.8.0-1')
        self.assertEqual(providers, {'pkg-config': 'pkgconf'})

    def test_both_providers_stop(self):
        with self.assertRaisesRegex(RuntimeError, 'Both'):
            p.choose_roots({'pkgconf:amd64': row('pkgconf'), 'pkg-config:amd64': row('pkg-config')}, {})

    def test_unknown_pkgconf_stop(self):
        with self.assertRaisesRegex(RuntimeError, 'absent'):
            p.choose_roots({'pkgconf:amd64': row('pkgconf')}, {})

    def test_invalid_provides_stop(self):
        with self.assertRaisesRegex(RuntimeError, 'provide'):
            p.choose_roots({'pkgconf:amd64': row('pkgconf')}, {('pkgconf', '1', 'amd64'): [{'Provides': 'pkg-config-fake'}]})

    def test_transaction_removal_downgrade_stop(self):
        for action in ('remove', 'downgrade', 'reinstall'):
            with self.subTest(action=action), self.assertRaises(RuntimeError):
                p.validate_transaction([{'name': 'a', 'version': '2', 'architecture': 'amd64', 'old_version': '1', 'action': action}], {'a:amd64': row()})

    def test_transaction_hold_stop(self):
        with self.assertRaisesRegex(RuntimeError, 'held'):
            p.validate_transaction([{'name': 'a', 'version': '2', 'architecture': 'amd64', 'old_version': '1', 'action': 'upgrade'}], {'a:amd64': row(held=True)})

    def test_transaction_old_version_stale_stop(self):
        with self.assertRaisesRegex(RuntimeError, 'Base'):
            p.validate_transaction([{'name': 'a', 'version': '2', 'architecture': 'amd64', 'old_version': '0', 'action': 'upgrade'}], {'a:amd64': row()})

    def test_inventory_exact_expected_upgrade(self):
        p.validate_inventory_delta({'a:amd64': row()}, {'a:amd64': row(version='2')},
                                   [{'name': 'a', 'version': '2', 'architecture': 'amd64'}])

    def test_inventory_unknown_addition_or_removal(self):
        for after in ({}, {'a:amd64': row(), 'x:amd64': row('x')}):
            with self.subTest(after=after), self.assertRaises(RuntimeError):
                p.validate_inventory_delta({'a:amd64': row()}, after, [])


class TestNativeClosureAndAPTPlans(unittest.TestCase):
    def test_actual_provider_selected_not_unsatisfied_candidate(self):
        a, b, old = version(1, 'a'), version(2, 'provider'), version(2, 'provider', '0')
        a.depends_list = {'Depends': [[dep(old, b)]]}
        actual = p.closure_versions({1: a, 2: b}, [a])
        self.assertEqual({v.parent_pkg.name for v in actual}, {'a', 'provider'})

    def test_all_installed_satisfied_alternatives_are_covered(self):
        a, b, c = version(1, 'a'), version(2, 'b'), version(3, 'c')
        a.depends_list = {'Depends': [[dep(b), dep(c)]]}
        self.assertEqual(len(p.closure_versions({1: a, 2: b, 3: c}, [a])), 3)

    def test_predepends_cycle_terminates(self):
        a, b = version(1, 'a'), version(2, 'b')
        a.depends_list = {'PreDepends': [[dep(b)]]}
        b.depends_list = {'Pre-Depends': [[dep(a)]]}
        self.assertEqual(len(p.closure_versions({1: a, 2: b}, [a])), 2)

    def test_missing_native_satisfier_stop(self):
        a, b = version(1, 'a'), version(2, 'b')
        a.depends_list = {'Depends': [[dep(b)]]}
        with self.assertRaisesRegex(RuntimeError, 'unsatisfied'):
            p.closure_versions({1: a}, [a])

    def test_simulation_versions(self):
        text = 'Inst a [1] (2 Ubuntu:22.04/jammy-updates [amd64])\nInst b (1 Ubuntu:22.04/jammy [amd64])\nConf a (2 Ubuntu [amd64])\n'
        self.assertEqual(p.parse_simulation(text), {'a': '2', 'b': '1'})

    def test_simulation_removal_stop(self):
        for text in ('Remv pkg-config [1]', 'Purg pkgconf [1]', 'Inst a unknown'):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                p.parse_simulation(text)

    def test_archive_uri_cache_filename(self):
        text = "Reading package lists...\n'file:/candidate/repo/pool/a.deb' a_1%3a2_amd64.deb 42 MD5Sum:abc\n"
        self.assertEqual(p.parse_archive_uris(text)[0]['cache_name'], 'a_1%3a2_amd64.deb')

    def test_archive_uri_external_or_traversal_stop(self):
        for text in ("'https://evil/a.deb' a.deb 42 MD5Sum:abc", "'file:/pool/a.deb' ../a.deb 42 MD5Sum:abc"):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                p.parse_archive_uris(text)


class TestProviderArchiveBytes(unittest.TestCase):
    def archive(self, symlink=False):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:') as archive:
            info = tarfile.TarInfo('./usr/bin/' + ('pkgconf' if symlink else 'pkg-config'))
            info.size = 4
            archive.addfile(info, io.BytesIO(b'good'))
            if symlink:
                link = tarfile.TarInfo('./usr/bin/pkg-config'); link.type = tarfile.SYMTYPE; link.linkname = 'pkgconf'
                archive.addfile(link)
        return buffer.getvalue()

    def test_regular_provider_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'usr/bin').mkdir(parents=True); (root / 'usr/bin/pkg-config').write_bytes(b'good')
            p.verify_provider_member(self.archive(), root)
            (root / 'usr/bin/pkg-config').write_bytes(b'evil')
            with self.assertRaisesRegex(RuntimeError, 'differs'):
                p.verify_provider_member(self.archive(), root)

    def test_pkgconf_symlink_and_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'usr/bin').mkdir(parents=True); (root / 'usr/bin/pkgconf').write_bytes(b'good')
            (root / 'usr/bin/pkg-config').symlink_to('pkgconf')
            p.verify_provider_member(self.archive(True), root)
            (root / 'usr/bin/pkg-config').unlink(); (root / 'usr/bin/pkg-config').symlink_to('/usr/bin/pkgconf')
            with self.assertRaisesRegex(RuntimeError, 'alias'):
                p.verify_provider_member(self.archive(True), root)

    def test_candidate_file_row(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); file = root / 'file'; file.write_text('data')
            result = p.file_row(root, file)
            self.assertEqual(result['ref'], {'base': 'candidate', 'path': 'file'})
            self.assertEqual(result['sha256'], p.sha(file))


class TestVerifiedDownloads(unittest.TestCase):
    class Response(io.BytesIO):
        status = 200

    def test_hash_checked_before_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'package.deb'
            opener = types.SimpleNamespace(open=lambda *args, **kwargs: self.Response(b'good'))
            with mock.patch.object(p.urllib.request, 'build_opener', return_value=opener):
                p.download_verified(p.ORIGIN + 'pool/a.deb', path, 4, hashlib.sha256(b'good').hexdigest())
            self.assertEqual(path.read_bytes(), b'good')
            self.assertFalse(path.with_name(path.name + '.partial').exists())

    def test_bad_hash_never_committed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'package.deb'
            opener = types.SimpleNamespace(open=lambda *args, **kwargs: self.Response(b'evil'))
            with mock.patch.object(p.urllib.request, 'build_opener', return_value=opener), self.assertRaises(RuntimeError):
                p.download_verified(p.ORIGIN + 'pool/a.deb', path, 4, hashlib.sha256(b'good').hexdigest())
            self.assertFalse(path.exists())

    def test_oversize_never_committed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'package.deb'
            opener = types.SimpleNamespace(open=lambda *args, **kwargs: self.Response(b'too-large'))
            with mock.patch.object(p.urllib.request, 'build_opener', return_value=opener), self.assertRaises(RuntimeError):
                p.download_verified(p.ORIGIN + 'pool/a.deb', path, 4, 'a' * 64)
            self.assertFalse(path.exists())

    def test_other_origin_rejected_before_network(self):
        with mock.patch.object(p.urllib.request, 'build_opener') as network, self.assertRaises(RuntimeError):
            p.download_verified('https://evil/a', Path('/tmp/not-written'), 4, 'a' * 64)
        network.assert_not_called()

    def test_existing_bad_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'package.deb'; path.write_bytes(b'old!')
            with self.assertRaises(RuntimeError):
                p.download_verified(p.ORIGIN + 'pool/a.deb', path, 4, hashlib.sha256(b'good').hexdigest())
            self.assertEqual(path.read_bytes(), b'old!')


class TestNativeAPTHelper(unittest.TestCase):
    def test_native_api_plan_and_full_closure(self):
        a, old_a, b = version(1, 'a', '2'), version(1, 'a'), version(2, 'b')
        pkg_a, pkg_b = a.parent_pkg, b.parent_pkg
        pkg_a.current_ver = old_a; pkg_a.version_list = [a]; pkg_a.essential = False
        pkg_b.current_ver = b; pkg_b.version_list = [b]; pkg_b.essential = False
        a.depends_list = {'Depends': [[dep(b)]]}
        class Cache(dict):
            packages = [pkg_a, pkg_b]
        cache = Cache(a=pkg_a, b=pkg_b)
        class DC:
            broken_count = 0
            def __init__(self, cache): self.marked = set(); self.candidates = {}
            def set_candidate_ver(self, pkg, candidate): self.candidates[pkg.id] = candidate
            def get_candidate_ver(self, pkg): return self.candidates.get(pkg.id, pkg.current_ver)
            def mark_install(self, pkg, *args): self.marked.add(pkg.id)
            def marked_install(self, pkg): return pkg.id in self.marked
            def marked_upgrade(self, pkg): return False
            def marked_delete(self, pkg): return False
            def marked_downgrade(self, pkg): return False
            def marked_reinstall(self, pkg): return False
        fake = types.SimpleNamespace(VERSION='2.4.fixture', config={}, init_config=lambda: None,
            read_config_file=lambda *args: None, init_system=lambda: None, Cache=lambda *args: cache,
            DepCache=DC, ProblemResolver=lambda *args: types.SimpleNamespace(protect=lambda *args: None, resolve=lambda *args: True))
        with tempfile.TemporaryDirectory() as temp:
            input_path, output_path = Path(temp) / 'input', Path(temp) / 'output'
            input_path.write_text(json.dumps({'config': 'fixture', 'roots': {'a': '2'}}))
            with mock.patch.dict(sys.modules, {'apt_pkg': fake}):
                p.native_solve(input_path, output_path)
            result = json.loads(output_path.read_text())
        self.assertEqual([r['name'] for r in result['closure']], ['a', 'b'])
        self.assertEqual(result['transaction'][0]['old_version'], '1')
        self.assertEqual(result['transaction'][0]['action'], 'upgrade')


if __name__ == '__main__':
    unittest.main()
