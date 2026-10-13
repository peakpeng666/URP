"""Read-only input/hash preflight. Does not import or execute any research module or policy."""
import ast, collections, datetime, difflib, hashlib, json, pathlib, sys
import numpy as np
H=pathlib.Path('/workspace/scratch/27470b7a9f17/independent_bpp_prefix_selection_20261006')
A=pathlib.Path(__file__).resolve().parent
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
sha=lambda x:hashlib.sha256(x).hexdigest()
freeze=json.loads((H/'FREEZE.json').read_bytes())
expected='883780fb58189db4159a0e2c99b4c2db43b4b98a36ade8387b795973b5dc153a'
assert sha((H/'FREEZE.json').read_bytes())==expected
for path,h in freeze['files'].items():
    assert (H/path).resolve().is_relative_to(H)
    assert sha((H/path).read_bytes())==h,path
p=json.loads((H/'PROTOCOL.json').read_bytes());NS='bpp_prefix_selection_20261006_v1'
assert p['namespace']==NS
seed=lambda *parts:int.from_bytes(hashlib.sha256((NS+'|'+'|'.join(map(str,parts))).encode()).digest()[:16],'big')
def generated(family,n,seed_value):
    r=np.random.Generator(np.random.PCG64(seed_value))
    if family=='weibull_3_45': raw=r.weibull(3,n)*45
    elif family=='uniform_1_100':raw=r.integers(1,101,n)
    elif family=='small_beta_2_5':raw=r.beta(2,5,n)*100
    elif family=='large_beta_5_2':raw=r.beta(5,2,n)*100
    elif family=='normal_50_15':raw=r.normal(50,15,n)
    elif family=='bimodal_20_30_70_80':
        coin=r.integers(0,2,n);lo=r.integers(20,31,n);hi=r.integers(70,81,n);raw=np.where(coin==0,lo,hi)
    else:raise AssertionError(family)
    return np.rint(np.clip(raw,1,100)).astype(np.int64).tolist(),int((raw<1).sum()),int((raw>100).sum())
by_group=collections.defaultdict(list);ids=set();seeds_by_split=collections.defaultdict(set);multisets=collections.defaultdict(set);prefixes=collections.defaultdict(set);suffixes=collections.defaultdict(set)
for meta in p['instances']:
    ident=meta['instance_id'];assert ident not in ids;ids.add(ident)
    d=json.loads((H/'inputs'/f'{ident}.json').read_bytes())
    for k,v in meta.items():assert d[k]==v,(ident,k)
    assert d['n']==5000 and d['capacity']==100
    x=d['items'];assert len(x)==5000 and all(type(a)==int and 1<=a<=100 for a in x)
    assert meta['multiset_sha256']==sha(canon(sorted(x)).encode())
    by_group[meta['group_id']].append(d);multisets[meta['split']].add(meta['multiset_sha256'])
    f=meta['family'];o=meta['order'];split=meta['split']
    if split in ('train','confirmation'):
        vs=seed(split,f,meta['replicate'],'values');ps=seed(split,f,meta['replicate'],'permutation')
        assert meta['value_seed']==vs and meta['permutation_seed']==ps
        base,below,above=generated(f,5000,vs)
        perm=np.random.Generator(np.random.PCG64(ps)).permutation(5000).tolist()
        positions=perm if o=='random' else sorted(range(5000),key=lambda j:base[j],reverse=o=='descending')
        assert d['source_position']==positions and sorted(positions)==list(range(5000))
        assert x==[base[j] for j in positions]
        seeds_by_split[split].update((vs,ps))
    else:
        assert split=='risk'
        vs=seed('risk',f,'prefix');ps=seed('risk',f,'suffix_permutation')
        assert meta['prefix_seed']==vs and meta['suffix_permutation_seed']==ps
        pre,below,above=generated(f,500,vs);tail=list(range(1,101))*45
        perm=np.random.Generator(np.random.PCG64(ps)).permutation(4500).tolist()
        expected_tail=[tail[j] for j in perm] if o=='random' else sorted(tail,reverse=o=='descending')
        assert x==pre+expected_tail and meta['prefix_sha256']==sha(canon(pre).encode())
        prefixes[meta['group_id']].add(sha(canon(x[:500]).encode()));suffixes[meta['group_id']].add(sha(canon(x[500:]).encode()))
        seeds_by_split[split].update((vs,ps))
    assert meta['raw_below_1']==below and meta['raw_above_100']==above
for group,rows in by_group.items():
    assert len(rows)==3 and {r['order'] for r in rows}=={'random','ascending','descending'}
    assert len({r['split'] for r in rows})==1 and len({r['multiset_sha256'] for r in rows})==1
for left,right in [('train','confirmation'),('train','risk'),('confirmation','risk')]:
    assert not multisets[left]&multisets[right]
    assert not seeds_by_split[left]&seeds_by_split[right]
assert all(len(x)==1 for x in prefixes.values()) and all(len(x)==3 for x in suffixes.values())
counts=dict(collections.Counter(r['split'] for r in p['instances']));assert counts=={'train':144,'confirmation':108,'risk':12}
groups={s:len({r['group_id'] for r in p['instances'] if r['split']==s}) for s in counts};assert groups=={'train':48,'confirmation':36,'risk':4}
assert len(ids)==264 and len(list((H/'inputs').glob('*.json')))==264
assert 144*2+108*4+12*4==p['counts']['total_full_policy_stream_runs']==768
source_results={}
for name in ['BF','published_EoH']:
    old=H.parent/'independent_bpp_distribution_20261006'/'sources'/f'{name}.py.txt';new=H/'sources'/f'{name}.py.txt'
    assert new.read_bytes()==old.read_bytes();assert sha(new.read_bytes())==p['policy_hashes'][name]
    source_results[name]=sha(new.read_bytes())
syntax={}
for f in sorted((H/'src').glob('*.py')):
    try:
        ast.parse(f.read_text(),filename=str(f));syntax[f.name]={'sha256':sha(f.read_bytes()),'passed':True}
    except SyntaxError as e:
        syntax[f.name]={'sha256':sha(f.read_bytes()),'passed':False,'line':e.lineno,'error':str(e)}
        assert str(f.relative_to(H)) not in freeze['files'],'Frozen executable must parse'
old=json.loads((H/'evidence/PREEXEC_FREEZE_v0.json').read_bytes());a=json.loads((H/'evidence/PREEXEC_AMENDMENT.json').read_bytes())
v1=json.loads((H/'evidence/PREEXEC_FREEZE_v1.json').read_bytes())
assert sha((H/'evidence/PREEXEC_FREEZE_v1.json').read_bytes())=='b7f64c13e3cbf5146b458f9b7f93264b71abd5363f0a8d445cc977cace955235'
changed=[n for n in old['files'] if old['files'][n]!=v1['files'][n]];assert changed==['src/check.py']
changed_v2=[n for n in v1['files'] if v1['files'][n]!=freeze['files'][n]];assert sorted(changed_v2)==['PROTOCOL.json','src/prepare.py','src/run.py']
for archived,current in [('PREEXEC_PROTOCOL_v1.json','PROTOCOL.json'),('PREEXEC_run_v1.py.txt','src/run.py'),('PREEXEC_prepare_v1.py.txt','src/prepare.py')]:
    assert sha((H/'evidence'/archived).read_bytes())==v1['files'][current]
assert sha((H/'evidence/PREEXEC_check_v0.py.txt').read_bytes())==a['old_check_sha256']
assert sha((H/'src/check.py').read_bytes())==a['new_check_sha256']
diff=''.join(difflib.unified_diff((H/'evidence/PREEXEC_check_v0.py.txt').read_text().splitlines(True),(H/'src/check.py').read_text().splitlines(True),fromfile='v0 checker',tofile='revised checker'))
outputs={s:len(list((H/s).glob('*'))) for s in ['raw','analysis','figures']}
markers={f:(H/f).exists() for f in ['RUN_STARTED.json','RUN_COMPLETE.json','RUN_FAILURE.json','MODEL.json','MODEL_FREEZE.json','CHECK.json','ANALYSIS_COMPLETE.json']}
assert all(v==0 for v in outputs.values()) and not any(markers.values())
result={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'kind':'pre-execution read-only integrity and input-lineage audit; no policy or research module executed','freeze_sha256':expected,'freeze_entries_verified':len(freeze['files']),'streams':counts,'multiset_groups':groups,'total_items_verified':264*5000,'policy_runs_executed_by_auditor':0,'expected_policy_runs':768,'input_reconstruction':'all values, rounding, clipping counts, seeds, original positions and permutations match independent generator implementation','split_seed_and_multiset_disjointness':'pairwise pass','risk_groups_identical_prefix_and_distinct_suffix_orders':4,'source_byte_equality':source_results,'python_source_syntax_and_hashes':syntax,'v0_to_v1_changed_existing_files':changed,'v1_to_v2_changed_existing_files':changed_v2,'v0_checker_diff':diff,'preexecution_output_directory_counts':outputs,'preexecution_markers':markers,'environment':{'python':sys.version,'numpy':np.__version__},'audit_script_sha256':sha(pathlib.Path(__file__).read_bytes())}
(A/'PREFLIGHT_MACHINE_CHECKS.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(result,indent=2,ensure_ascii=False))
