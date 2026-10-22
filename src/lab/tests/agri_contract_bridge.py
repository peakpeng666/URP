"""Cross-language agri contract check. Invoked by frontend/tools/check-agri-contract.mjs.
Loads the real backend validator, not a copied TS geometry approximation.
"""
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
source = Path(__file__).resolve().parents[1] / 'urp_lab/scenarios/validate.py'
spec = importlib.util.spec_from_file_location('agri_actual_validator', source)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
results = []
for record in json.loads(Path(sys.argv[1]).read_text()):
    scenario = record['scenario']
    result = {'pattern': record['pattern'], 'seed': record['seed']}
    try:
        normalized = validator.validate_instance(scenario['problem_class'], scenario['instance'])
        if scenario['problem_class'] == 'fleet_routing':
            assert len(normalized['tasks']) == scenario['editable']['values']['task_count']
            assert normalized['vehicles']['count'] == scenario['editable']['values']['vehicles']
        result['valid'] = True
    except Exception as error:
        result.update(valid=False, error=f'{type(error).__name__}: {error}')
    results.append(result)
print(json.dumps({'checked': len(results), 'passed': sum(r['valid'] for r in results), 'results': results}, ensure_ascii=False, indent=2))
sys.exit(0 if all(r['valid'] for r in results) else 1)
