# Seeds two derived run records into the TEMP runtime only (gateway must be stopped: store holds an exclusive lock).
import copy, os, sys
assert os.environ['URP_LAB_RUNTIME'].startswith('/home/peakpeng/urp-e2e/')
from urp_lab.store import Store
from urp_lab.result_integrity import without_invalidated_results
from urp_lab import paths
st = Store(paths.RUNTIME / 'lab.sqlite3')
src = st.get_run(sys.argv[1])
q = copy.deepcopy(src); q['run_id'] = 'run_e2e_quarantined_unverified'; q['label'] = 'e2e 隔离样本 source_identity_verified=false'
q['process']['source_identity_verified'] = False
q.update(state='error', error='执行期间来源身份核对失败：e2e 注入样本'); q.update(without_invalidated_results(q))
l = copy.deepcopy(src); l['run_id'] = 'run_e2e_legacy_noidentity'; l['label'] = 'e2e 旧记录 无身份字段'
l['process'].pop('source_identity_verified', None)
st.put_run(q); st.put_run(l); st.close(); print('seeded from', sys.argv[1], 'state/process of src:', src.get('state'), src.get('process'))
