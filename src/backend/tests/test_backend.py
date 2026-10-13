"""Offline unit and loopback HTTP tests using explicitly synthetic fixtures only."""
import copy, hashlib, http.client, json, tempfile, threading, unittest
from pathlib import Path
from backend.store import Store, StoreError
from backend.server import make_server


def fixture(id='model-fixture',status='completed'):
    comparison=dict(metric='heldout_gap',unit='percent',direction='min',cohort='test-fixture-only',protocol='fixed-protocol',budget='16000 generated tokens',aggregation='mean',reference='frozen baseline')
    return dict(schema_version=1,id=id,title='Synthetic backend test fixture',domain='test',kind='model_ablation',status=status,
      started_at=None,finished_at=None,counts=[dict(unit='run',value=None,scope='new_model_requests',note='not observed')],failure_reason=None,
      notes=['TEST FIXTURE; no real model calls'],parameters={'model':'fixture-model','reasoning_effort':'medium','generation_token_limit':16000},provenance={'captured_at':'test','source_label':'unit-test'},
      metrics=[dict(id='a',label='first',algorithm='a',value=2.5,comparison=comparison,source={'artifact_id':'report','locator':'/a'}),dict(id='b',label='second',algorithm='b',value=1.0,comparison=comparison,source={'artifact_id':'report','locator':'/b'})],
      artifacts=[dict(id='report',path='report.json',media_type='application/json',role='results')])

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'store.sqlite3');self.package=self.root/'package';self.package.mkdir();self.d=fixture();self.write()
    def tearDown(self):self.tmp.cleanup()
    def write(self,d=None):
        if d is not None:self.d=d
        (self.package/'experiment.json').write_text(json.dumps(self.d));(self.package/'report.json').write_text('{"a":2.5,"b":1.0}')
    def items(self,*ids):return [dict(experiment_id=self.d['id'],metric_id=id) for id in ids]
    def test_idempotent_import_and_version_history(self):
        first=self.store.import_package(self.package);second=self.store.import_package(self.package);self.assertFalse(first['reused']);self.assertTrue(second['reused']);self.assertEqual(second['revision'],1)
        old=copy.deepcopy(self.d);self.d['notes'].append('new observation');self.write();third=self.store.import_package(self.package);self.assertEqual(third['revision'],2)
        self.write(old);self.assertTrue(self.store.import_package(self.package)['reused']);self.assertEqual(self.store.get(self.d['id'])['revision'],2);self.assertEqual(self.store.get(self.d['id'],1)['notes'],old['notes'])
    def test_same_contract_compare(self):
        self.store.import_package(self.package);r=self.store.compare(self.items('a','b'));self.assertEqual(r['differences_from_first'],[0,-1.5])
    def test_incomparable_budget_and_cohort_rejected(self):
        for key in ['budget','cohort','protocol','unit','reference','aggregation','metric','direction']:
            self.write(fixture());self.d['metrics'][1]['comparison']=dict(self.d['metrics'][1]['comparison']);self.d['metrics'][1]['comparison'][key]='max' if key=='direction' else 'different';self.write();self.store.import_package(self.package)
            with self.assertRaisesRegex(StoreError,key):self.store.compare(self.items('a','b'))
    def test_unknown_is_not_zero_and_model_metadata_roundtrips(self):
        self.d['metrics'][1]['value']=None;self.write();self.store.import_package(self.package);d=self.store.get(self.d['id']);self.assertIsNone(d['counts'][0]['value']);self.assertEqual(d['parameters']['reasoning_effort'],'medium')
        with self.assertRaisesRegex(StoreError,'按0'):self.store.compare(self.items('a','b'))
    def test_running_failed_and_unknown_are_never_complete(self):
        for status in ['running','queued','failed','partial','unknown']:
            d=fixture(status=status);d['failure_reason']='recorded test failure' if status=='failed' else None;self.write(d);self.store.import_package(self.package);self.assertEqual(self.store.get(d['id'])['status'],status)
            with self.assertRaises(StoreError):self.store.compare(self.items('a','b'))
        self.assertEqual(self.store.get(d['id'],3)['failure_reason'],'recorded test failure')
    def test_source_bytes_immutable_after_import(self):
        before=(self.package/'report.json').read_bytes();self.store.import_package(self.package);(self.package/'report.json').write_text('changed source');ref,data=self.store.artifact(self.d['id'],'report');self.assertEqual(data,before);self.assertEqual(ref['sha256'],hashlib.sha256(data).hexdigest())
    def test_traversal_and_symlinks_rejected_atomically(self):
        outside=self.root/'outside.json';outside.write_text('{}');self.d['artifacts'][0]['path']='../outside.json';self.write()
        with self.assertRaises(StoreError):self.store.import_package(self.package)
        self.d['artifacts'][0]['path']='link.json';(self.package/'link.json').symlink_to(outside);self.write()
        with self.assertRaises(StoreError):self.store.import_package(self.package)
        self.assertEqual(self.store.list(),[])
    def test_credentials_rejected_without_partial_import(self):
        self.d['parameters']['api_key']='test-not-a-real-secret';self.write()
        with self.assertRaisesRegex(StoreError,'凭据'):self.store.import_package(self.package)
        self.write(fixture());(self.package/'report.json').write_text(json.dumps({'password':'test-only-long-password-value'}))
        with self.assertRaisesRegex(StoreError,'凭据'):self.store.import_package(self.package)
        self.assertEqual(self.store.list(),[])
    def test_http_end_to_end_import_query_compare_download(self):
        server=make_server(self.store,self.root,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(method,path,payload=None):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5);body=json.dumps(payload) if payload is not None else None;conn.request(method,path,body,{'Content-Type':'application/json'});r=conn.getresponse();data=r.read();headers=dict(r.getheaders());status=r.status;conn.close();return status,headers,data
        try:
            self.assertEqual(request('GET','/api/health')[0],200)
            self.assertEqual(json.loads(request('POST','/api/import',{'package':'package'})[2])['revision'],1)
            self.assertTrue(json.loads(request('POST','/api/import',{'package':'package'})[2])['reused'])
            d=json.loads(request('GET','/api/experiments/model-fixture')[2]);self.assertEqual(d['status'],'completed')
            comparison=json.loads(request('POST','/api/compare',{'items':self.items('a','b')})[2]);self.assertEqual(comparison['differences_from_first'],[0,-1.5])
            status,headers,data=request('GET','/api/experiments/model-fixture/artifacts/report');self.assertEqual(status,200);self.assertEqual(headers['X-Content-SHA256'],hashlib.sha256(data).hexdigest())
            self.assertEqual(request('POST','/api/import',{'package':'../outside'})[0],400)
        finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
