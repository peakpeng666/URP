"""Presentation-only rerender from existing frozen-analysis outputs; no statistics rerun."""
import pathlib,json,csv,textwrap,hashlib,os
import numpy as np
H=pathlib.Path(__file__).resolve().parent
files=['analysis/SUMMARY.json','analysis/family_order_summary.csv','analysis/risk_per_stream.csv','analysis/cluster_bootstrap.npz']
before={p:hashlib.sha256((H/p).read_bytes()).hexdigest() for p in files}
s=json.loads((H/'analysis/SUMMARY.json').read_bytes());overall=s['confirmation'];familyorder=list(csv.DictReader((H/'analysis/family_order_summary.csv').open()));riskrows=list(csv.DictReader((H/'analysis/risk_per_stream.csv').open()))
for r in familyorder:r['selector_minus_SBS']=float(r['selector_minus_SBS'])
for r in riskrows:r['selector_regret']=int(r['selector_regret'])
source=(H/'src/analyze.py').read_text();block=source.split('    # Three concise Chinese figures;')[1];block=block.split("    put(H/'ANALYSIS_COMPLETE.json'")[0];block=block.split('\n',1)[1];block=textwrap.dedent(block)
block=block.replace("plt.rcParams['font.family']='Noto Sans CJK SC'", "from matplotlib import font_manager; font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'; font_manager.fontManager.addfont(font); plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()")
block=block.replace("ax.bar(labels,values,color=['#65849c','#daa64c','#a593ba','#327a64','#999999','#363d48'])","ax.scatter(labels,values,c=['#65849c','#daa64c','#a593ba','#327a64','#999999','#363d48'],s=70,zorder=3);ax.grid(axis='y',alpha=.2)")
exec(compile(block,'<unchanged_plot_block_with_explicit_font>','exec'),globals())
assert before=={p:hashlib.sha256((H/p).read_bytes()).hexdigest() for p in files}
r={'reason':'Font discovery failed under initial Matplotlib font family, producing Chinese tofu; explicitly register installed CJK TTC font','original_figures':'evidence/figures_before_font_fix','statistics_rerun':False,'presentation_note':'Mean comparison uses point plot on narrow y range instead of truncated baseline bars','data_hashes_unchanged':before,'font_path':font,'font_sha256':hashlib.sha256(pathlib.Path(font).read_bytes()).hexdigest(),'figures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'figures').glob('*.png')}}
(H/'evidence/FONT_RENDER_AMENDMENT.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False))
