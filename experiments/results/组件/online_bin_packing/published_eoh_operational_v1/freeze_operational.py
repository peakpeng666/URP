"""Static/hash freeze only; never import NumPy or run a packing algorithm."""
import argparse,ast,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
import run_batch,runtime
from integrity import digest

def entry(p):return {'bytes':p.stat().st_size,'sha256':digest(p)}
def main():
    a=argparse.ArgumentParser();a.add_argument('--output',choices=['prevalidation_freeze.json','operational_freeze.json'],required=True);args=a.parse_args()
    froot=ROOT.parent/'published_eoh_formula_v1';oldpath=froot/'static_preparation_freeze.json'
    if digest(oldpath)!='b33fe66403fcc2382213bb5a0255162a1362a02c6e7ecd942c471bcd530a51d1':raise ValueError('formula staticfreeze changed')
    old=json.loads(oldpath.read_text());refs=dict(old['reference_files']);refs[str(oldpath)]=entry(oldpath)
    for r in old['files']:
        p=froot/r['path']
        if entry(p)!={'bytes':r['bytes'],'sha256':r['sha256']}:raise ValueError('formula source changed')
        refs[str(p)]=entry(p)
    broot=ROOT.parent/'paper_baseline_v1'
    for rel in ['src/checker.py','data/historical_numeric.json','protocol.json','preparation_freeze.json','results/ff_bf_2024_data_batch_20261004_01/report.json']:
        p=broot/rel;refs[str(p)]=entry(p)
    for rel in ['results/numeric_gate_20261004_01/status.json','results/numeric_gate_20261004_01/stdout.bin','results/numeric_gate_20261004_01/stderr.bin','results/launch_numeric_gate_20261004_01/start_utc.txt','results/launch_numeric_gate_20261004_01/end_utc.txt']:
        p=froot/rel;refs[str(p)]=entry(p)
    package_inventories={}
    for package_root in [ROOT,froot,broot]:
        package_files=sorted(str(p.relative_to(package_root)) for p in package_root.rglob('*') if p.is_file() and p.suffix in {'.py','.pyc','.so','.pyd'})
        package_inventories[str(package_root)]=package_files
        for rel in package_files:
            p=package_root/rel
            if not p.is_relative_to(ROOT):refs[str(p)]=entry(p)
    runtime_files=dict(old['runtime_files'])
    for mod in list(sys.modules.values()):
        file=getattr(mod,'__file__',None)
        if file:
            p=pathlib.Path(file).resolve()
            if p.is_file() and not p.is_relative_to(ROOT) and not p.is_relative_to(ROOT.parent):runtime_files[str(p)]=entry(p)
    paths=[]
    for dirname in ['src','tests','logs']:
        paths.extend(p for p in (ROOT/dirname).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for name in ['freeze_operational.py','prepared_plan.json','protocol.json','README.md','preparation_costs.json']:
        p=ROOT/name
        if p.exists():paths.append(p)
    if args.output=='operational_freeze.json':
        if not (ROOT/'preparation_costs.json').is_file():raise ValueError('manualcosts notready')
        paths.extend(p for p in (ROOT/'results/manual_validation_01').rglob('*') if p.is_file())
    files=[]
    for p in sorted(set(paths)):
        if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p))
        files.append({'path':str(p.relative_to(ROOT)),**entry(p)})
    if 'numpy' in sys.modules:raise RuntimeError('unexpected NumPy import')
    d={k:old[k] for k in ['python_executable','python_prefix','python_base_prefix','python_exec_prefix','python_base_exec_prefix','python_executable_sha256','runtime_roots']}
    d.update({'identity':'p3_formula_operational_30_v1','scope':'Manual validation only until finalreviewedfreeze and separate30slotapproval','files':files,'runtime_files':runtime_files,'references':refs,'package_inventories':package_inventories,'numpy_imported_during_freeze':False,'runtime_note':'NumPy/source identity and selected standard-library hashes; not fullOShermeticity or untrustedcodeisolation'})
    p=ROOT/args.output
    with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
    print(json.dumps({'file':str(p),'sha256':digest(p),'files':len(files),'runtime_files':len(runtime_files),'references':len(refs)},indent=2))
if __name__=='__main__':main()
