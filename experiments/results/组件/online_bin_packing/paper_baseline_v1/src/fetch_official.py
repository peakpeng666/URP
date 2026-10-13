"""Read-only official raw-file retrieval; never imports downloaded Python."""
import concurrent.futures, hashlib, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
COMMIT='472545785c936dcfc863d2bc0d6109cf23c7ce62'
PATHS=['LICENSE','examples/bp_online/README.md','examples/bp_online/get_instance.py','examples/bp_online/prob.py','examples/bp_online/evaluation/evaluation.py','examples/bp_online/evaluation/runEval.py','examples/bp_online/evaluation/heuristic_first_fit.py','examples/bp_online/evaluation/heuristic_best_fit.py','examples/bp_online/testingdata/generate_instances.py']+[f'examples/bp_online/testingdata/{s}.pkl' for s in ['test_dataset_1k','test_dataset_5k','test_dataset_10k','training_dataset_5k']]
def fetch(path):
    url=f'https://raw.githubusercontent.com/FeiLiu36/EoH/{COMMIT}/{path}'
    with urllib.request.urlopen(url, timeout=40) as r: data=r.read(2_000_001)
    if len(data)>2_000_000: raise ValueError('response too large')
    tree=json.loads((ROOT/'upstream/tree_response.json').read_text())
    t=next(v for v in tree['tree'] if v['path']==path)
    gitsha=hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
    if gitsha!=t['sha'] or len(data)!=t['size']: raise ValueError('Git object mismatch')
    out=ROOT/'upstream'/path;out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as f:f.write(data)
    return {'path':path,'url':url,'bytes':len(data),'git_blob_sha1':gitsha,'sha256':hashlib.sha256(data).hexdigest()}
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(fetch,PATHS))
    (ROOT/'upstream/provenance.json').write_text(json.dumps({'repository':'https://github.com/FeiLiu36/EoH','commit':COMMIT,'files':rows},indent=2)+'\n')
    print(json.dumps(rows,indent=2))
