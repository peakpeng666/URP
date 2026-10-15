#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
manifest=json.loads((R/'src/research/configs/cvrplib_cases.json').read_text())
rows=[]
for c in manifest['cases']:
 for kind,path,expected in [('instance',c['instance_path'],c['instance_sha256']),('reference',c['reference']['path'],c['reference']['sha256'])]:
  actual=hashlib.sha256((R/path).read_bytes()).hexdigest();rows.append({'case_id':c['case_id'],'kind':kind,'path':path,'sha256':actual,'expected':expected,'pass':actual==expected})
print(json.dumps({'checked':len(rows),'passed':sum(x['pass'] for x in rows),'files':rows},indent=2))
raise SystemExit(0 if all(x['pass'] for x in rows) else 1)
