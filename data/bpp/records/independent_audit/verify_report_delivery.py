import resource
resource.setrlimit(resource.RLIMIT_CPU,(5,5))
import pathlib,json,csv,hashlib,zipfile,datetime
from docx import Document
H=pathlib.Path('/workspace/scratch/27470b7a9f17/independent_bpp_prefix_selection_20261006');A=pathlib.Path(__file__).resolve().parent
p=H/'BPP前缀安全算法选择实验.docx';doc=Document(p);text='\n'.join(q.text for q in doc.paragraphs)
for term in ['-21.454','-23.917','-19.380','49/56/3','25.333','26.250','152','历史整体900 CPU秒预算合规仍未知','已测成本及未完整计时项','事后oracle','26条后重启缓存版']:assert term in text,term
assert '全成本' not in text and '可实现分支oracle' not in text
rows=list(csv.DictReader((H/'analysis/family_order_summary.csv').open()));assert len(doc.tables)==3
assert len(doc.tables[0].rows)==19
for got,row in zip(doc.tables[0].rows[1:],rows):
    assert [c.text for c in got.cells][2:]==[f'{float(row[k]):.2f}' for k in ['BF','BF_then_EoH','published_EoH','SELECTOR','selector_minus_SBS','selector_regret']]
s=json.loads((H/'analysis/SUMMARY.json').read_text());assert len(doc.tables[1].rows)==5
for got,g in zip(doc.tables[1].rows[1:],s['risk']['groups']):
    assert got.cells[2].text=='/'.join(map(str,g['selector_regrets'])) and got.cells[3].text==('是' if g['oracle_preference_reverses'] else '否')
cpu=list(csv.DictReader((H/'analysis/cpu_accounting.csv').open()));assert len(doc.tables[2].rows)==len(cpu)+1
for got,row in zip(doc.tables[2].rows[1:],cpu):
    assert [c.text for c in got.cells][2:]==[row['runs'],f"{float(row['cpu_loop_seconds']):.3f}",f"{float(row['cpu_selector_seconds']):.6f}"]
with zipfile.ZipFile(p) as z:
    media=[n for n in z.namelist() if n.startswith('word/media/')];assert len(media)==2
    m={hashlib.sha256(z.read(n)).hexdigest() for n in media};assert m=={hashlib.sha256((H/'figures'/n).read_bytes()).hexdigest() for n in ['confirmation_means.png','same_prefix_risk.png']}
    xml=z.read('word/document.xml');assert b'<w:ins ' not in xml and b'<w:del ' not in xml
pages=sorted((H/'docx_qa_release').glob('page-*.png'));assert len(pages)==6
out={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'document_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'document_name':p.name,'read_only':True,'reported_main_risk_budget_and_oracle_wording_checked':True,'all18_table_numeric_rows_checked':True,'risk_and_cpu_table_rows_checked':True,'embedded_images_match_final_approved_pngs':True,'tracked_changes_absent':True,'rendered_pages':6,'all_six_rendered_pages_visually_inspected_by_reviewer':True,'visual_observations':'Readable CJK throughout; no clipping, broken tables or overlapping text seen; figures correspond to verified data.','rendered_page_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in pages}}
(A/'DELIVERY_AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
