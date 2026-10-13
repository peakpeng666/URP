"""Hash-only/static-parse preparation. Does not import NumPy or execute formulas."""
import argparse,ast,hashlib,importlib.metadata,json,os,pathlib,platform,re,resource,selectors,signal,subprocess,sys,sysconfig,time,traceback,warnings
ROOT=pathlib.Path(__file__).resolve().parent

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def row(p):return {'bytes':p.stat().st_size,'sha256':sha(p)}
def main():
    dist=importlib.metadata.distribution('numpy')
    if dist.version!='2.3.5':raise ValueError('expected installed NumPy2.3.5 metadata')
    base=pathlib.Path(dist.locate_file('')).resolve()
    roots=[base/'numpy',base/'numpy.libs',base/'numpy-2.3.5.dist-info']
    runtime={};root_inventories={}
    for root in roots:
        if not root.is_dir():raise ValueError('runtime root missing')
        paths=sorted(p for p in root.rglob('*') if p.is_file())
        root_inventories[str(root)]=sorted(str(p.relative_to(root)) for p in paths)
        for p in paths:runtime[str(p)]=row(p)
    for mod in list(sys.modules.values()):
        file=getattr(mod,'__file__',None)
        if file:
            p=pathlib.Path(file)
            if p.is_file() and not p.resolve().is_relative_to(ROOT):runtime[str(p.resolve())]=row(p)
    p=pathlib.Path(sysconfig.get_config_var('LIBDIR'))/sysconfig.get_config_var('LDLIBRARY')
    if p.is_file():runtime[str(p.resolve())]=row(p)
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.name!='static_preparation_freeze.json' and not any(x in p.parts for x in ['__pycache__','.authorization_uses','results']):
            if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p))
            if p.suffix=='.json':json.loads(p.read_text())
            files.append({'path':str(p.relative_to(ROOT)),**row(p)})
    references={}
    for p in sorted((ROOT.parent/'published_eoh_readiness/upstream').rglob('*')):
        if p.is_file():references[str(p.resolve())]=row(p)
    if 'numpy' in sys.modules:raise RuntimeError('unexpected NumPy import')
    d={'identity':'p3_formula_reimplementation_static_preparation_v1','authorization_state':'Static preparation only; numerical gate requires separate exact-digest one-use approval and coordinatedCPUwindow','files':files,'runtime_files':runtime,'runtime_roots':root_inventories,'reference_files':references,'python_executable':sys.executable,'python_executable_resolved':str(pathlib.Path(sys.executable).resolve()),'python_prefix':sys.prefix,'python_base_prefix':sys.base_prefix,'python_exec_prefix':sys.exec_prefix,'python_base_exec_prefix':sys.base_exec_prefix,'python_executable_sha256':sha(pathlib.Path(sys.executable)),'environment':{'python':sys.version,'numpy_metadata_version':dist.version,'numpy_package_root':str(base/'numpy'),'platform':platform.platform()},'validation':{'source_ast_and_json_parse':'passed','numpy_imported':False,'formula_or_numerical_calls':0,'formal_packing_calls':0},'limitations':['One handwritten formula with source mapping and analytic boundarychecks; no author-byte execution parity','Runtime hashes do not establish full OS/shared-library hermeticity or isolate untrusted programs','Formal30slot runner not implemented or authorized']}
    p=ROOT/'static_preparation_freeze.json'
    with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
    print(json.dumps({'sha256':sha(p),'files':len(files),'runtime_files':len(runtime),'runtime_inventory_entries':sum(map(len,root_inventories.values())),'reference_files':len(references),'numpy_imported':False},indent=2))
if __name__=='__main__':main()
