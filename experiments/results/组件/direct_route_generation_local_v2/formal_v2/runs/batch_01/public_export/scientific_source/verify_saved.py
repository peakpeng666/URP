"""Offline recomputation only; never starts models or solvers."""
import json
from pathlib import Path
from score_local import evaluate,summarize
P=Path(__file__).resolve().parents[1]
plan=json.loads((P/'protocol.json').read_text());saved=json.loads((P/'results.json').read_text());rows=[]
for slot in plan['slots']:
 i=slot['slot_index'];raw=P/'raw'/f'{i:02d}';execution=json.loads((raw/'result.json').read_text());instance=json.loads((P/slot['directory']/'instance.json').read_text())
 r=evaluate(slot,(raw/'response_body.json').read_bytes(),execution['http_status'],execution['process_status'],instance);old=saved['rows'][i]
 for key in ['transport_valid','route_feasible','fallback_used','model_cost','gap_pct','delivered_cost','delivered_routes','errors']:assert r[key]==old[key],(i,key)
 rows.append(r)
assert summarize(rows)==saved['summary']
print('PASS:8 saved outputs and primary summary reproduced; no model or solver calls')
