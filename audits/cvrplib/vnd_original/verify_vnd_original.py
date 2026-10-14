"""Read-only provenance closure: original ZIP -> declared member -> delivered bytes."""
import argparse, datetime, hashlib, json
from pathlib import Path
from zipfile import ZipFile
EXPECTED_SHA='4ac6eca8206577329f074d8aa57274202ce591681f9daeb939671ff8c302dbca'
EXPECTED_SIZE=1296035
ARCHIVE_NAME='experiments/results/路线求解/公共新16例算子顺序迁移.zip'
def sha(b): return hashlib.sha256(b).hexdigest()
def verify(archive,root):
 raw=archive.read_bytes(); manifest_path=root/'src/research/configs/cvrplib_sources.json';manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw)
 selected=[x for x in manifest['files'] if x.get('archive')==ARCHIVE_NAME]
 report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'read-only original archive/member/delivered-source provenance; no experiments or source changes','archive_bytes':len(raw),'archive_sha256':sha(raw),'expected_archive_bytes':EXPECTED_SIZE,'expected_archive_sha256':EXPECTED_SHA,'archive_matches':len(raw)==EXPECTED_SIZE and sha(raw)==EXPECTED_SHA,'source_manifest_path':str(manifest_path.relative_to(root)),'source_manifest_sha256':sha(manifest_raw),'member_count':len(selected),'expected_member_count':10,'members':[]}
 with ZipFile(archive) as z:
  names=z.namelist()
  for row in selected:
   item={'delivered_path':row['path'],'archive_member':row['member'],'declared_sha256':row['sha256'],'declared_bytes':row['bytes'],'member_occurrences':names.count(row['member']),'declared_archive_sha_matches':row['archive_sha256']==EXPECTED_SHA}
   if item['member_occurrences']==1:
    original=z.read(row['member']);current=(root/row['path']).read_bytes();item.update(original_member_sha256=sha(original),original_member_bytes=len(original),delivered_sha256=sha(current),delivered_bytes=len(current),byte_for_byte_equal=original==current)
    item['pass']=item['declared_archive_sha_matches'] and item['byte_for_byte_equal'] and sha(original)==row['sha256'] and len(original)==row['bytes']
   else:item['pass']=False
   report['members'].append(item)
 report['pass']=report['archive_matches'] and len(selected)==10 and all(x['pass'] for x in report['members'])
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.archive,a.root);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pass':r['pass'],'archive_matches':r['archive_matches'],'member_count':r['member_count'],'passed_members':sum(x['pass'] for x in r['members'])}));raise SystemExit(0 if r['pass'] else 1)
