"""Archive final artifacts and audit evidence; no scientific computation or retuning."""
import pathlib,json,hashlib,zipfile,time,shutil
H=pathlib.Path(__file__).resolve().parent;D=H.parent/'independent_bpp_prefix_selection_20261006_delivery';D.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
for n,h in json.loads((H/'FREEZE.json').read_bytes())['files'].items():assert sha((H/n).read_bytes())==h,n
assert json.loads((H/'CHECK.json').read_bytes())['passed']
assert json.loads((H/'independent_audit/FINAL_AUDIT.json').read_bytes())['scientific_result_status']=='PASS_WITH_DISCLOSED_VALIDATION_IO_AMENDMENT'
exclude_dirs={'.mplconfig','__pycache__','docx_qa','docx_qa_final'}
exclude_files={'MANIFEST.json','ARTIFACT_PACKAGE.log','ARTIFACT_PACKAGE_RESOURCE.json'}
paths=[p for p in sorted(H.rglob('*')) if p.is_file() and not set(p.relative_to(H).parts)&exclude_dirs and p.name not in exclude_files]
manifest={'schema':'delivered-file-manifest-v1','scientific_freeze_sha256':sha((H/'FREEZE.json').read_bytes()),'files':{str(p.relative_to(H)):{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in paths},'excluded_non_deliverable_intermediates':sorted(exclude_dirs),'packaging_own_cost':'Recorded in external final delivery acceptance receipt because it is only known after archive closes'}
(H/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');paths.append(H/'MANIFEST.json')
archive=D/'BPP前缀安全选择_完整源码数据与审计_20261006.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for p in paths:z.write(p,arcname=str(p.relative_to(H)),compress_type=zipfile.ZIP_STORED if p.suffix in ['.npz','.png','.docx','.pdf'] else zipfile.ZIP_DEFLATED)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for n,meta in manifest['files'].items():assert sha(z.read(n))==meta['sha256'],n
r={'archive_name':archive.name,'archive_path':str(archive),'archive_sha256':sha(archive.read_bytes()),'archive_bytes':archive.stat().st_size,'zip_members':len(paths),'manifest_entries_checked':len(manifest['files']),'scientific_result':'PASS_WITH_DISCLOSED_VALIDATION_IO_AMENDMENT','historical_total_900_cpu_compliance':'NOT_ESTABLISHED','docx_path':str(H/'BPP前缀安全算法选择实验.docx'),'docx_sha256':sha((H/'BPP前缀安全算法选择实验.docx').read_bytes()),'manifest_sha256':sha((H/'MANIFEST.json').read_bytes())}
(D/'PACKAGE_VERIFICATION.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False))
