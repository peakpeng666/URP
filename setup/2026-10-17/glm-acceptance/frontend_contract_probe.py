"""Reproduce editor/API and recommendation capability mismatches without changing saved data."""
from pathlib import Path
import argparse
import copy
import json
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src/lab'))
from urp_lab.scenarios.validate import validate_instance
from urp_lab.recommend import recommend

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
out = parser.parse_args().out
if not out.is_absolute():
    parser.error('--out must be an absolute path')
out.mkdir(parents=True, exist_ok=False)
base = json.loads((Path(__file__).parent / 'unload-free.json').read_text())['instance']
changed = copy.deepcopy(base)
changed['depot'] = [10, 15]  # exactly what both existing editor controls update
after = validate_instance('fleet_routing', changed)
scenario = {'problem_class': 'fleet_routing', 'frame': {'kind': 'field'}, 'cost_unit': 's'}
hetero = copy.deepcopy(base)
hetero['vehicles'] = {'fleet': [{'count': 1, 'capacity': 16}, {'count': 1, 'capacity': 20}], 'travel': 'free'}
recommendation = recommend(scenario, validate_instance('fleet_routing', hetero))
data = {
    'depot_editor_roundtrip': {'before': base['depot'], 'edited_depot': changed['depot'],
                             'submitted_depots': changed['depots'], 'persisted_depot': after['depot'],
                             'expected_edit_preserved': True, 'actual_edit_preserved': after['depot'] == changed['depot']},
    'hetero_recommendation': {k: recommendation[k] for k in ['compare', 'ranking']},
}
(out / 'frontend-contract.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(data, ensure_ascii=False))
