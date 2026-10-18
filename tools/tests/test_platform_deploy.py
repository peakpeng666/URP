"""Recovery must reject corruption and never operate on an unrelated container."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('deploy', Path(__file__).resolve().parents[1] / 'platform_deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class Response(io.BytesIO):
    def __init__(self, data, status, headers):
        super().__init__(data)
        self.status, self.headers = status, headers


class DeploymentTests(unittest.TestCase):
    def test_resume_then_validate_full_hash(self):
        data = b'complete published image fragment'
        asset = {'name': 'image.part000', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'image.part000.partial').write_bytes(data[:8])
            def open_request(request, **kwargs):
                self.assertEqual(request.headers['Range'], 'bytes=8-')
                return Response(data[8:], 206, {'Content-Range': f'bytes 8-{len(data)-1}/{len(data)}'})
            with patch.object(deploy.urllib.request, 'urlopen', side_effect=open_request):
                target = deploy.download(asset, root, 'test-release')
            self.assertEqual(target.read_bytes(), data)
            target.write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                deploy.download(asset, root, 'test-release')
            self.assertEqual(target.read_bytes(), b'corrupted')

    def test_wrong_range_is_not_appended(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            partial = root / 'image.part000.partial'
            partial.write_bytes(b'123')
            response = Response(b'456', 206, {'Content-Range': 'bytes 1-3/6'})
            with patch.object(deploy.urllib.request, 'urlopen', return_value=response), self.assertRaises(ValueError):
                deploy.download({'name': 'image.part000', 'bytes': 6, 'sha256': ''}, root, 'test')
            self.assertEqual(partial.read_bytes(), b'123')

    def test_foreign_container_is_rejected(self):
        foreign = {'Config': {'Labels': {deploy.LABEL: 'other-version'}}}
        with patch.object(deploy, 'inspect', return_value=foreign), self.assertRaises(ValueError):
            deploy.owned_container('existing-work', 'expected-version')

    def test_live_listener_is_not_mistaken_for_time_wait(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            with self.assertRaises(ValueError):
                deploy.available(listener.getsockname()[1])

    def test_api_shutdown_keeps_real_nonzero_exit(self):
        accepted = subprocess.CompletedProcess([], 0, stdout='{"accepted":true}', stderr='')
        state = {'State': {'ExitCode': 1, 'Running': False}}
        with patch.object(deploy.subprocess, 'run', return_value=accepted), \
                patch.object(deploy, 'owned_container', return_value=state), \
                self.assertRaisesRegex(RuntimeError, 'actual exit code 1'):
            deploy.stop_container('ours', 'commit')

    def test_shutdown_signal_fallback_is_not_declared_success(self):
        unavailable = subprocess.CompletedProcess([], 1, stdout='', stderr='connection refused')
        state = {'State': {'ExitCode': 0, 'Running': False}}
        with patch.object(deploy.subprocess, 'run', return_value=unavailable), \
                patch.object(deploy, 'owned_container', return_value=state), \
                self.assertRaisesRegex(RuntimeError, 'signal fallback'):
            deploy.stop_container('ours', 'commit')

    def test_supplement_rejects_escaping_members_and_links(self):
        for name in ['project/../../etc/passwd', '/project/file', 'host/etc/passwd']:
            with self.assertRaises(ValueError):
                deploy.supplement_member(tarfile.TarInfo(name))
        link = tarfile.TarInfo('project/link'); link.type = tarfile.SYMTYPE
        link.linkname = '../../outside'
        with self.assertRaises(ValueError):
            deploy.supplement_member(link)

    def test_supplement_remaps_long_python_link(self):
        link = tarfile.TarInfo('project/env/bin/python'); link.type = tarfile.SYMTYPE
        link.linkname = '../../../python/cpython-3.12/bin/python'
        link.pax_headers = {'path': link.name, 'linkpath': link.linkname}
        result = deploy.supplement_member(link)
        self.assertEqual(result.name, 'env/bin/python')
        self.assertEqual(result.linkname, '/home/peakpeng/.local/share/uv/python/cpython-3.12/bin/python')
        self.assertEqual(result.pax_headers, {})


if __name__ == '__main__':
    unittest.main()
