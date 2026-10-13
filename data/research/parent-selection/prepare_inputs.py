#!/usr/bin/env python3
"""Copy only terminal, already evaluated evidence. Never load candidates as code."""
import hashlib,json,pathlib,shutil,datetime
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT.parent
files=[('urp132_20261005_b01_numerical_state/rows.json','raw/phase0/rows.json'),('urp132_20261005_b01_numerical_state/panel.json','raw/phase0/panel.json'),('urp132_20261005_b01_numerical_state/registry.json','raw/phase0/registry.json'),('urp132_20261005_b01_numerical_state/report-df2812a963cdd1053991b98aae52d5d5ecff8c8b141d05f360737d11d056e325.json','raw/phase0/terminal_report.json'),('glm53_fixed_design_followon_20261005/CANDIDATES.json','raw/followon/CANDIDATES.json'),('glm53_fixed_design_followon_20261005/RESULTS.json','raw/followon/RESULTS.json'),('glm53_fixed_design_followon_20261005/REGISTRY.json','raw/followon/REGISTRY.json'),('glm53_fixed_design_followon_20261005/PLAN.json','raw/followon/PLAN.json'),('frozen_design_controls_20261005/RESULTS.json','raw/controls/RESULTS.json')]
files += [(str(p.relative_to(BASE)),'raw/phase0/bundles/'+p.name) for p in sorted((BASE/'urp132_20261005_b01_numerical_state/bundles').glob('*.json'))]
manifest={'schema':'selection-replay-input-manifest-v1','copied_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[],'no_active_60_slot_protocol_inputs':True,'new_candidate_executions':0,'new_model_calls':0,'historical_score_rows':45}
for src,dst in files:
 p,q=BASE/src,ROOT/dst;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 a,b=hashlib.sha256(p.read_bytes()).hexdigest(),hashlib.sha256(q.read_bytes()).hexdigest();assert a==b
 manifest['files'].append({'original_path':src,'copy_path':dst,'sha256':a,'bytes':q.stat().st_size})
(ROOT/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
print('Copied',len(files),'terminal evidence files')
