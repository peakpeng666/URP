import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import textwrap
import unittest
from unittest.mock import patch

R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('workflow_contract',R/'verify_workflow_contract.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)

def body(marker):
    s=W.TEMPLATE.split("<<'"+marker+"'\n",1)[1].split('\n          '+marker,1)[0]
    return textwrap.dedent(s)+'\n'

class WorkflowTests(unittest.TestCase):
    def test_full_parity(self):
        anchor='a'*64
        W.verify_text(W.render(anchor),anchor)
        for old,new in [('ubuntu-22.04','ubuntu-24.04'),('contents: read','contents: write'),('fix/agriculture-compatibility-20261022','main'),('paths: [.github/workflows/f2c-capability.yml]','paths: ["**"]'),('--execute-capability-probe','--unsafe'),('-I -B -S','-I -B')]:
            with self.subTest(old=old),self.assertRaises(ValueError):
                W.verify_text(W.render(anchor).replace(old,new),anchor)
    def test_all_shell_bodies_bound_stderr_without_masking_failure(self):
        bodies=W.render('a'*64).split('        run: |\n')[1:]
        self.assertEqual(len(bodies),5)
        for body in bodies:
            first=body.splitlines()[0].strip()
            self.assertEqual(first,'exec 2>/dev/null')
            result=subprocess.run(['/bin/bash','-c',first+"\nprintf '/home/private/token https://private.invalid' >&2; exit 23"],capture_output=True,text=True,env={'PATH':'/usr/bin:/bin'})
            self.assertEqual((result.returncode,result.stdout,result.stderr),(23,'',''))
    def test_invalid_anchors(self):
        for value in ('','x'*64,'a'*63,'a'*65,'A'*64,'a'*64+'\n'):
            with self.subTest(value=value),self.assertRaises(ValueError): W.render(value)
    def test_source_index_only_materialization(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); source=base/'recipe-source/deploy/f2c-capability';source.mkdir(parents=True)
            target=base/'target';target.mkdir()
            (source/'recipe').mkdir();data=b'VALUE=1\n';(source/'recipe/demo.py').write_bytes(data)
            raw=json.dumps({'schema':1,'status':'reviewed-source','identity':'jammy-rootless-capability-v1','files':{'recipe/demo.py':{'sha256':hashlib.sha256(data).hexdigest()}}}).encode()
            (source/'source-index.json').write_bytes(raw)
            (source/'candidate-workflow.yml').write_text('UNINDEXED MUST NOT COPY')
            env={'GITHUB_WORKSPACE':str(base),'CANDIDATE_ROOT':str(target),'REVIEWED_SOURCE_INDEX_SHA256':hashlib.sha256(raw).hexdigest()}
            with patch.dict(os.environ,env,clear=True): exec(body('PY_ANCHOR'),{})
            self.assertEqual((target/'recipe/demo.py').read_bytes(),data)
            self.assertFalse((target/'candidate-workflow.yml').exists())
    def test_anchor_rejects_symlink_and_hardlink(self):
        for kind in ('symlink','hardlink'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                base=Path(d); source=base/'recipe-source/deploy/f2c-capability';source.mkdir(parents=True)
                target=base/'target';target.mkdir();original=base/'original';original.write_bytes(b'x')
                path=source/'x'
                if kind=='symlink':path.symlink_to(original)
                else:os.link(original,path)
                raw=json.dumps({'schema':1,'status':'reviewed-source','identity':'jammy-rootless-capability-v1','files':{'x':{'sha256':hashlib.sha256(b'x').hexdigest()}}}).encode()
                (source/'source-index.json').write_bytes(raw)
                env={'GITHUB_WORKSPACE':str(base),'CANDIDATE_ROOT':str(target),'REVIEWED_SOURCE_INDEX_SHA256':hashlib.sha256(raw).hexdigest()}
                with patch.dict(os.environ,env,clear=True),self.assertRaises(AssertionError):exec(body('PY_ANCHOR'),{})
    def test_reporting_bootstrap_uses_only_verified_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'recipe').mkdir()
            reporter=b"assert _VERIFIED_PUBLIC_CODES_BYTES==b'{}';print('SAFE')\n"
            files={'recipe/report_capability_status.py':reporter,'recipe/public_codes.json':b'{}'}
            for name,data in files.items():(root/name).write_bytes(data)
            raw=json.dumps({'files':{k:{'sha256':hashlib.sha256(v).hexdigest()} for k,v in files.items()}}).encode()
            (root/'source-index.json').write_bytes(raw)
            env={'CANDIDATE_ROOT':str(root),'REVIEWED_SOURCE_INDEX_SHA256':hashlib.sha256(raw).hexdigest()}
            for valid in (True,False):
                if not valid:(root/'recipe/public_codes.json').write_bytes(b'{"secret":"/home/private/token"}')
                out=io.StringIO()
                with patch.dict(os.environ,env,clear=True),contextlib.redirect_stdout(out):exec(body('PY_REPORT'),{})
                self.assertEqual(out.getvalue(),'SAFE\n' if valid else 'stage=report status=FAIL code=UNKNOWN\n')

if __name__=='__main__':unittest.main()
