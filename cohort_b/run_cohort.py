"""Explicit run entry for separately frozen native cohort B. No auto launch."""
from pathlib import Path
import sys,json,hashlib,datetime,argparse
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'src/research/src'))
from urp_research.cvrplib.io import parse_vrp
from run_vendor import run

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--host-id',required=True,choices=['cloud','local']);args=ap.parse_args()
 if not args.run:raise SystemExit('Use --run only in reserved timing window after independent admission.')
 freeze=json.loads((ROOT/'COHORT_FREEZE.json').read_text())
 for p,h in freeze['files'].items():
  if sha(ROOT/p)!=h:raise RuntimeError('frozen source changed '+p)
 out=ROOT/('formal-runs-'+args.host_id);out.mkdir(exist_ok=True)
 binaries=[ROOT/'sisr/build/sisr_adapter']+list((ROOT/'ails/classes').rglob('*.class'))
 (out/'host_build.json').write_text(json.dumps({'host_id':args.host_id,'binaries':{str(p.relative_to(ROOT)):sha(p) for p in binaries}},indent=2))
 cases=json.loads((ROOT.parent/'src/research/configs/cvrplib_cases.json').read_text())['cases'];cases={c['case_id']:c for c in cases}
 for row in freeze['schedule']:
  if row['host_id']!=args.host_id:continue
  key=f"{row['algorithm']}__{row['case_id']}__s{row['seed']}";dest=out/(key+'.json')
  if dest.exists():continue
  c=cases[row['case_id']];raw=ROOT.parent/c['instance_path']
  if sha(raw)!=c['instance_sha256']:raise RuntimeError('input identity changed')
  parsed=parse_vrp(raw.read_text());p={k:parsed[k] for k in ['coordinates','demands','capacity']};p.update(K=c['n_customers'],seed=row['seed'])
  if c['contract']['vehicle_limit'] is not None or c['contract']['id']!='standard-X-unlimited':raise RuntimeError('non-unrestricted case')
  started=out/(key+'.started.json')
  if started.exists():raise RuntimeError('uncertain prior launch; reconcile before retry '+key)
  started.write_text(json.dumps({'key':key,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
  result=run(row['algorithm'],p,5);result.update(case_id=c['case_id'],instance_sha256=c['instance_sha256'],contract=c['contract'],cohort='vendor_X12',host_id=args.host_id)
  tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2));tmp.replace(dest)
  print(key,result['status'],flush=True)
if __name__=='__main__':main()
