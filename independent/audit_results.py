"""Audit saved CVRP runs against raw instance bytes; preserves failed attempts."""
import argparse
from collections import Counter
from validate import *

def audit(root, result_dir, planned):
    manifest=root/'src/research/configs/cvrplib_cases.json'
    cases={c['case_id']:c for c in json.loads(manifest.read_text())['cases']}
    rows=[]; keys=[]; errors=[]
    for path in sorted(result_dir.rglob('*.json')):
        record=json.loads(path.read_text())
        if not isinstance(record,dict) or record.get('schema')!='urp-cvrplib-result-v1':continue
        c=cases[record['case_id']]; p=read_instance(root/c['instance_path'])
        k=c['contract']['vehicle_limit'] or len(p['demands'])-1
        checked=check_result(p,record,k)
        identity=[]
        if sha(root/c['instance_path'])!=c['instance_sha256']:identity.append('raw instance hash mismatch')
        if record.get('contract',{}).get('K')!=k:identity.append('vehicle contract mismatch')
        for field, expected in [('instance_sha256',c['instance_sha256']),('case_manifest_sha256',sha(manifest))]:
            if field in record and record[field]!=expected: identity.append(field+' mismatch')
        # Independently rebuild the exact reference-free payload serialization.
        payload={'coordinates':[[float(x),float(y)] for x,y in p['coordinates']], 'demands':p['demands'],
                 'capacity':p['capacity'],'K':k,'algorithm':record['algorithm'],'seed':record['seed'],'budget_seconds':record['budget_seconds']}
        digest=hashlib.sha256(json.dumps(payload,separators=(',',':'),sort_keys=True,allow_nan=False).encode()).hexdigest()
        if record.get('payload_sha256')!=digest:identity.append('payload hash mismatch')
        if identity:checked['eligible']=False
        key=(record['case_id'],record['algorithm'],record['seed'],record['budget_seconds'])
        keys.append(key)
        if identity or (checked['claimed_feasible'] and not checked['eligible']):errors.append(str(path))
        rows.append({'file':str(path.relative_to(result_dir)),'sha256':sha(path),'case_id':record['case_id'],'algorithm':record['algorithm'], 'seed':record['seed'],'identity_errors':identity,**checked})
    duplicates=[list(k) for k,v in Counter(keys).items() if v>1]
    if planned<len(rows):raise ValueError('planned denominator smaller than result count')
    return {'planned':planned,'attempted':len(rows),'not_started':planned-len(rows),'eligible':sum(r['eligible'] for r in rows),
            'status_counts':dict(Counter(r['status'] for r in rows)),'duplicate_keys':duplicates,'audit_errors':errors,'rows':rows}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result_dir',type=Path);parser.add_argument('--planned',type=int,required=True)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); report=audit(args.root,args.result_dir,args.planned)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
    raise SystemExit(1 if report['audit_errors'] or report['duplicate_keys'] else 0)
