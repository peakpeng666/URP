import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
raw=[('X-n101-k25','R','RC',7,11,17,1),('X-n106-k14','E','C',3,11,17,2),('X-n110-k13','C','R',None,11,17,3),('X-n204-k19','C','RC',6,11,17,23),('X-n209-k16','E','R',None,11,17,24),('X-n214-k11','C','C',4,11,17,25),('X-n303-k21','C','C',8,12,18,44),('X-n308-k13','E','RC',6,12,18,45),('X-n313-k71','R','RC',3,12,18,46),('X-n502-k39','E','C',3,12,18,69),('X-n513-k21','C','RC',4,12,18,70),('X-n524-k153','R','R',None,13,19,71)]
items=[]
for name,dep,cust,k,tab,page,row in raw:
 items.append(dict(case_id=name,customer_distribution=cust,customer_clusters=k,depot_position=dep,table=tab,printed_page=page,pdf_page_1based=page+1,row=row,verification='visually_checked_rendered_pdf_2026-10-15',screenshot=f'evidence/cvrp-table{page+1}.png'))
out={'schema':'urp-cvrplib-distribution-metadata-v1','source_url':'https://optimization-online.org/wp-content/uploads/2014/10/4597.pdf','pdf_sha256':hashlib.sha256((root/'protocol/evidence/uchoa_benchmark.pdf').read_bytes()).hexdigest(),'customer_legend':{'R':'random','C':'clustered','RC':'mixed random and clustered'},'depot_legend':{'R':'random','C':'central','E':'eccentric'},'scope':'Generator metadata, not fitted spatial classification or agricultural validation','family_metadata':{'A':{'customer_distribution':'R','source_section':'2, printed page3'},'B':{'customer_distribution':'C','source_section':'2, printed page3'},'P':{'customer_distribution':'unknown','note':'capacity variants; do not assign one spatial class to whole family'},'E':{'customer_distribution':'unknown'},'F':{'customer_distribution':'unknown'}},'cases':items}
(root/'protocol/distribution_metadata.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
# Join verified X metadata to all canonical selected problems.
cases=json.loads((root/'src/research/configs/cvrplib_cases.json').read_text())
by_id={x['case_id']:x for x in out['cases']}; out['x_cases']=out.pop('cases');out['cases']=[]
for c in cases['cases']:
 row={k:c[k] for k in ['case_id','base_id','n_customers','size_stratum','source_family','instance_sha256']};row['contract_id']=c['contract']['id']
 row.update(by_id.get(c['case_id'],dict(customer_distribution=out['family_metadata'].get(c['source_family'],{}).get('customer_distribution','unknown'),verification='source_family_metadata_only',source_section=out['family_metadata'].get(c['source_family'],{}).get('source_section'))));out['cases'].append(row)
(root/'protocol/distribution_metadata.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
