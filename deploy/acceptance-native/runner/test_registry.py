import io,json,pathlib,socket,ssl,tempfile,unittest,urllib.error
from unittest.mock import Mock
from runner.verify_registry import fetch_metadata,verify,CheckError
from public_summary import registry_projection

class Response(io.BytesIO):
    def geturl(self):return 'https://registry.npmjs.org/public/1'

class RegistryTests(unittest.TestCase):
    def test_transient_retry_and_bounded_exhaustion(self):
        for first in (urllib.error.HTTPError('PRIVATE',429,'PRIVATE',{},None),urllib.error.HTTPError('PRIVATE',503,'PRIVATE',{},None),socket.timeout('PRIVATE')):
            opener=Mock(side_effect=[first,Response(b'{"dist":{"integrity":"sha512-ok"}}')]);sleep=Mock()
            metadata,attempts=fetch_metadata('https://registry.npmjs.org/public/1',opener,sleep)
            self.assertEqual(attempts,2);sleep.assert_called_once_with(2)
        opener=Mock(side_effect=socket.timeout('PRIVATE'));sleep=Mock()
        with self.assertRaises(CheckError) as caught:fetch_metadata('PRIVATE',opener,sleep)
        self.assertEqual(caught.exception.attempts,3);self.assertEqual(opener.call_count,3)
    def test_auth_missing_not_retried(self):
        for code in (401,403,404):
            opener=Mock(side_effect=urllib.error.HTTPError('PRIVATE',code,'PRIVATE',{},None));sleep=Mock()
            with self.assertRaises(CheckError) as caught:fetch_metadata('PRIVATE',opener,sleep)
            self.assertEqual(caught.exception.http_status,code);self.assertEqual(opener.call_count,1);sleep.assert_not_called()
    def test_non_timeout_network_and_tls_not_retried(self):
        for cause,expected in ((OSError('PRIVATE_DNS'),'network'),(ssl.SSLError('PRIVATE_TLS'),'tls')):
            opener=Mock(side_effect=urllib.error.URLError(cause));sleep=Mock()
            with self.assertRaises(CheckError) as caught:fetch_metadata('PRIVATE',opener,sleep)
            self.assertEqual(caught.exception.category,expected);self.assertEqual(opener.call_count,1);sleep.assert_not_called()

    def test_integrity_fail_closed_and_safe_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/'src/frontend';path.mkdir(parents=True)
            (path/'package-lock.json').write_text(json.dumps({'packages':{'node_modules/PRIVATE':{'resolved':'https://registry.npmmirror.com/PRIVATE','version':'1','integrity':'sha512-original'}}}))
            fetch=Mock(return_value=({'dist':{'integrity':'sha512-mismatch'}},1))
            result=verify(tmp,fetch)
            self.assertEqual(result['status'],'failed');self.assertEqual(result['phase'],'integrity_check')
            self.assertEqual(result['mirror_index'],1);fetch.assert_called_once()
            self.assertNotIn('PRIVATE',json.dumps(result))
            fetch=Mock(side_effect=CheckError('http',403,1));result=verify(tmp,fetch)
            self.assertEqual(result['phase'],'metadata_fetch');self.assertEqual(result['http_status'],403)
            result=verify(tmp,Mock(return_value=({'dist':{'integrity':'sha512-original','tarball':'https://registry.npmjs.org/PRIVATE'}},1)))
            self.assertEqual(result['status'],'passed');self.assertEqual(result['mirror_identities_verified'],1)
            result=verify(tmp,Mock(return_value=({'dist':{'integrity':'sha512-original','tarball':'https://registry.npmjs.org/OTHER'}},1)))
            self.assertEqual(result['error'],'tarball_path_mismatch')
    def test_reducer_drops_unknown_fields(self):
        result=registry_projection({'phase':'PRIVATE','status':'PRIVATE','error':'PRIVATE','http_status':'PRIVATE','mirror_index':True,'attempts':999,'raw':'PRIVATE'})
        self.assertNotIn('PRIVATE',json.dumps(result));self.assertIsNone(result['mirror_index']);self.assertIsNone(result['attempts'])

if __name__=='__main__':unittest.main()
