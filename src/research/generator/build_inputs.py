"""Offline extraction from the already-delivered package; never contacts a provider."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/workspace/shared/audit64k/candidate/original132_p2_budget64k_implemented_disabled_20261007')
sha = lambda b: hashlib.sha256(b).hexdigest()
manifest = json.loads((SOURCE / 'DELIVERY_MANIFEST.json').read_bytes())['members']
used = {}

def source(relative):
    raw = (SOURCE / relative).read_bytes()
    digest = sha(raw)
    assert manifest[SOURCE.name + '/' + relative] == digest, relative
    used[relative] = digest
    return raw

roster = json.loads(source('package/inputs/roster.json'))
freeze = json.loads(source('package/inputs/freeze.json'))
config_raw = source('package/inputs/config.raw.json')
route = json.loads(source('package/inputs/input-route.json'))
baseline_path = Path('/workspace/shared/audit64k/baseline/evidence/ROSTER.original.json')
baseline_raw = baseline_path.read_bytes()
baseline = json.loads(baseline_raw)['records']
rows = roster['records']
assert len(rows) == 60 and [r['order'] for r in rows] == list(range(73, 133))
assert collections.Counter(r['arm'] for r in rows) == {'EOH_TC': 30, 'IID_TC': 30}
assert route['route'] == 'stdin'
packs = []
for old, row in zip(baseline, rows, strict=True):
    for key in ('slot_id', 'order', 'position', 'arm', 'parents', 'prompt_sha256', 'serialized_messages_sha256'):
        assert old[key] == row[key], (row['slot_id'], key)
    pack = json.loads(source('package/inputs/packs/' + row['slot_id'] + '.json'))
    assert sha(pack['prompt'].encode()) == row['prompt_sha256'] == pack['prompt_sha256']
    assert pack['parents'] == row['parents']
    assert pack['configuration'] == freeze['configuration']
    # Literal parent bytes are already inside the unchanged prompt; no re-rendering.
    messages = [{'role': 'system', 'content': json.loads(config_raw)['agent']['candidate']['prompt']},
                {'role': 'user', 'content': pack['prompt']}]
    canonical = json.dumps(messages, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    assert sha(canonical) == row['serialized_messages_sha256']
    packs.append({'record': row, 'pack': pack})
value = {'revision': 'minimal-local-execution-r1', 'roster': roster, 'freeze': freeze,
         'config_raw': config_raw.decode(), 'slots': packs}
raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
(ROOT / 'frozen_inputs.json').write_bytes(raw)
provenance = {
    'source_package': str(SOURCE), 'source_drive_file_id': '1qV-kqfQ9qwOcDNtzoRWAbfMiJz_Iaz3i',
    'source_zip_sha256_parent_supplied': '6a2f77e86391cb6639276d789f211f33cfed6a86142d9208315130c76f8147df',
    'zip_rehashed_here': False, 'selected_members_verified_against_delivery_manifest': used,
    'baseline_roster_path': str(baseline_path), 'baseline_roster_sha256': sha(baseline_raw),
    'baseline_60_prompt_parent_order_message_hashes_unchanged': True,
    'frozen_inputs_sha256': sha(raw), 'slot_count': 60, 'arms': {'EOH_TC': 30, 'IID_TC': 30},
    'parent_draw_count_including_duplicates': sum(len(s['pack']['parents']) for s in packs),
    'real_cli_invocations': 0, 'new_external_transmissions': 0,
    'old_production_state_read_or_modified': False,
    'denied_first_slot_zip_accessed': False,
}
(ROOT / 'input_provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'frozen_inputs_sha256': sha(raw), 'slots': len(packs), 'source_files_checked': len(used)}))
