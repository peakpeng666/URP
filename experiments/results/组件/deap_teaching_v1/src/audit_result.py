"""Independent saved-result audit; imports neither DEAP nor the optimizer."""
import hashlib
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[1]
r = json.loads((root/'results/run.json').read_text())
p = json.loads((root/'results/protocol_frozen.json').read_text())
c = p['config']
assert r['config'] == c
assert r['budget'] == r['evaluations'] == len(r['ledger']) == c['population']*(c['generations']+1)
assert r['source_sha256'] == p['source_sha256'] == hashlib.sha256((root/'src/sphere_ga.py').read_bytes()).hexdigest()
for i, row in enumerate(r['ledger'], 1):
    assert row['evaluation'] == i and len(row['x']) == c['dimension']
    assert all(math.isfinite(v) and c['lower'] <= v <= c['upper'] for v in row['x'])
    assert math.fsum(v*v for v in row['x']) == row['value']
assert len(r['history']) == c['generations']+1
for g, row in enumerate(r['history']):
    assert row['generation'] == g
    assert row['evaluations'] == (g+1)*c['population']
    assert row['best'] == min(x['value'] for x in r['ledger'][:row['evaluations']])
    assert row['best'] == math.fsum(v*v for v in row['x'])
    assert any(row['x'] == x['x'] for x in r['ledger'][:row['evaluations']])
assert len(r['final_population']) == c['population']
for row in r['final_population']:
    assert row['value'] == math.fsum(v*v for v in row['x'])
    assert any(row['x'] == x['x'] and row['value'] == x['value'] for x in r['ledger'])
assert min(x['value'] for x in r['final_population']) == r['history'][-1]['best']
report = {'passed': True, 'objective_calls_in_audit': 0,
          'saved_evaluations_recomputed': len(r['ledger']), 'history_rows_checked': len(r['history']),
          'note': 'Recomputed saved Sphere arithmetic only; no optimizer rerun or extra formal sample.',
          'run_sha256': hashlib.sha256((root/'results/run.json').read_bytes()).hexdigest()}
(root/'results/postrun_audit.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
