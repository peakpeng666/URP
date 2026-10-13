"""Regenerate the offline reader from the single canonical Markdown corpus."""
from pathlib import Path
import json, re, os, html
from urllib.parse import unquote
import markdown
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CAT = json.loads((ROOT/'文献目录.json').read_text()) if (ROOT/'文献目录.json').exists() else json.loads((ROOT/'资料/文献目录.json').read_text())
CAT_BY_PATH = {x['path']: x for x in CAT}

def render(source, path):
    formulas=[]
    def protect(match):
        block=match.group(0).startswith('\\[')
        formula=match.group(0)[2:-2]
        token=f'URPMATHPLACEHOLDER{len(formulas)}END'
        formulas.append((token,formula,block))
        return '\n\n'+token+'\n\n' if block else token
    text=re.sub(r'\\\[.*?\\\]|\\\(.*?\\\)',protect,source,flags=re.S)
    result=markdown.markdown(text,extensions=['tables','fenced_code','sane_lists','attr_list'])
    for token,formula,block in formulas:
        tag='div' if block else 'span'
        value=f'<{tag} class="math" data-display="{str(block).lower()}" data-math="{html.escape(formula,quote=True)}"></{tag}>'
        result=result.replace('<p>'+token+'</p>',value).replace(token,value)
    soup=BeautifulSoup(result,'html.parser')
    for element in soup.find_all(['script','iframe','object','embed','form','input','button']):element.decompose()
    for element in soup.find_all(True):
        for attr in list(element.attrs):
            if attr.lower().startswith('on'):del element.attrs[attr]
    for a in soup.find_all('a',href=True):
        url=a['href'];target,sep,fragment=url.partition('#')
        if re.match(r'(?:javascript|data|vbscript):',url,re.I):
            del a['href'];continue
        if target and not re.match(r'[A-Za-z][A-Za-z0-9+.-]*:',target):
            full=(path.parent/unquote(target)).resolve()
            relative=os.path.relpath(full,ROOT)
            a['href']=relative+(sep+fragment if sep else '')
            if full.suffix=='.md' and full.is_relative_to(ROOT):a['data-local']=relative
            if full.name=='参考证据.jsonl':a['data-local']=relative
            if full.is_dir() and full.name=='逐篇笔记':a['data-topic']=full.parent.name
        else:
            a['target']='_blank';a['rel']='noopener noreferrer'
    for img in soup.find_all('img',src=True):
        if not re.match(r'[A-Za-z][A-Za-z0-9+.-]*:',img['src']):
            img['src']=os.path.relpath((path.parent/unquote(img['src'])).resolve(),ROOT)
        img['loading']='lazy'
    for table in soup.find_all('table'):
        wrap=soup.new_tag('div',attrs={'class':'tablewrap'});table.wrap(wrap)
    return str(soup)

entries=[]
mds=[ROOT/'README.md',ROOT/'综合分析.md',*sorted((ROOT/'专题').glob('*.md')),ROOT/'待补文献.md',*sorted((ROOT/'笔记').rglob('*.md')),ROOT/'教材/README.md']
for p in mds:
    if not p.exists():continue
    text=p.read_text();path=str(p.relative_to(ROOT));parts=p.relative_to(ROOT).parts
    theme=parts[1] if parts[0]=='笔记' else '总览'
    kind='逐篇笔记' if '逐篇笔记' in parts else '研究专题' if parts[0]=='专题' else '综述与索引'
    title=re.sub(r'^#\s*','',text.splitlines()[0])
    ids=CAT_BY_PATH.get(path,{}).get('source_ids',[])
    aliases=' '.join(ids)
    entries.append({'path':path,'title':title,'topic':theme,'kind':kind,
                    'ids':[x.lower() for x in ids],
                    'html':render(text,p),'search':(title+' '+aliases+' '+text).lower()})

for p in sorted((ROOT/'笔记').glob('*/参考证据.jsonl')):
    rows=[json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    out=['<h1>原文定位</h1>']
    for r in rows:
        identity=r.get('claim_id',r.get('id',r.get('evidence_id','')))
        out.append('<section class="evidence"><h2>'+html.escape(str(identity))+'</h2><dl>')
        for key,value in r.items():
            if key.startswith('_') or key in ['claim_id','id','evidence_id']:continue
            names={'paper_id':'文献','claim':'内容','pdf_pages':'PDF页码','locator':'定位',
                   'assessment':'分析','uncertainty':'待核','evidence_kind':'证据类型'}
            if value is None or value=='':continue
            if isinstance(value,(dict,list)):value=json.dumps(value,ensure_ascii=False)
            out.append('<dt>'+html.escape(names.get(key,key))+'</dt><dd>'+html.escape(str(value))+'</dd>')
        out.append('</dl></section>')
    entries.append({'path':str(p.relative_to(ROOT)),'title':p.parent.name[3:]+' · 原文定位',
                    'topic':p.parent.name,'kind':'参考证据','html':'\n'.join(out),
                    'search':p.read_text().lower()})

payload=json.dumps(entries,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
template=r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>URP文献</title><link rel="stylesheet" href="资料/阅读资源/katex.min.css">
<style>
*{box-sizing:border-box}body{margin:0;color:#1b2b30;background:#f2f4f1;font:16px/1.8 system-ui,-apple-system,"Noto Sans CJK SC","Microsoft YaHei",sans-serif}header{padding:20px 30px;background:#193d38;color:white;display:flex;align-items:baseline;gap:24px;flex-wrap:wrap}header h1{margin:0;font-size:25px}header p{margin:0;color:#d0dfd8;font-size:14px}header a{color:#e0ede6;font-size:14px}.layout{display:grid;grid-template-columns:330px minmax(0,1fr)}aside{padding:20px;background:#e9eee9;border-right:1px solid #d1dbd1;position:sticky;top:0;height:100vh;overflow:auto}input,select,button{font:inherit;border:1px solid #bdc9bf;border-radius:6px;background:white;padding:9px;color:#1b2b30}input,select{width:100%;margin:0 0 10px}input:focus,select:focus,button:focus-visible{outline:2px solid #30675d;outline-offset:2px}#count{font-size:13px;color:#56685a;margin:10px 0}#list button{display:block;text-align:left;width:100%;margin:7px 0;padding:10px 12px;line-height:1.45;font-size:14px;border:1px solid #d5dfd5;cursor:pointer}#list button:hover,#list button.active{border-color:#326b60;background:#f4faf5}#list small{display:block;color:#69796d;margin-top:5px;font-size:11px}.pager{display:flex;gap:10px}.pager button{font-size:13px;cursor:pointer}main{padding:30px 4vw 70px;max-width:1450px;width:100%;margin:auto;background:#fff;min-height:100vh}article h1{font-size:28px;line-height:1.45;margin:0 0 28px;color:#193d38}article h2{font-size:21px;margin:36px 0 14px;border-bottom:1px solid #d7dfd7;padding-bottom:8px;color:#193d38}article h3{font-size:18px;margin:24px 0 10px}article p{margin:15px 0;overflow-wrap:anywhere}a{color:#186653;text-underline-offset:3px}li{margin:8px 0;overflow-wrap:anywhere}code{background:#f0f3ef;padding:1px 4px;border-radius:3px;font-size:.9em;overflow-wrap:anywhere}pre{white-space:pre-wrap;padding:18px;background:#f0f3ef;overflow-wrap:anywhere}ul{padding-left:24px}.tablewrap{overflow:auto;margin:20px 0}table{border-collapse:collapse;min-width:100%;font-size:14px}td,th{border:1px solid #d3dcd3;padding:10px;vertical-align:top;min-width:95px}th{text-align:left;background:#e8f0e9}tr:nth-child(even){background:#f8faf8}img{max-width:100%;height:auto}dl{display:grid;grid-template-columns:110px minmax(0,1fr);gap:8px 16px}dt{font-weight:600;color:#586b5d}dd{margin:0;overflow-wrap:anywhere}#navline{font-size:13px;color:#647569;margin-bottom:20px;display:flex;justify-content:space-between;gap:20px}.math[data-display="true"]{overflow-x:auto;padding:8px 0}.katex{font-size:1.08em}.evidence h2{font-size:18px}.notice{color:#5e7062;font-size:14px}button:disabled{opacity:.45;cursor:default}@media(max-width:850px){.layout{grid-template-columns:1fr}aside{position:relative;height:auto;max-height:48vh}main{padding:24px}#list{max-height:23vh;overflow:auto}article h1{font-size:24px}header{padding:18px 24px}dl{grid-template-columns:90px minmax(0,1fr)}}@media print{header,aside,#navline{display:none}.layout{display:block}main{padding:0}article{font-size:11pt}a{color:inherit}h2,h3{break-after:avoid}}
</style><script src="资料/阅读资源/katex.min.js"></script></head>
<body><header><h1>URP文献</h1><p>16个主题 · 565份笔记</p><a href="#README.md" data-home>目录</a><a href="#综合分析.md" data-summary>综合分析</a></header>
<div class="layout"><aside><label for="q">查找论文、方法或正文</label><input id="q" type="search" placeholder="P177、Adam、算法选择…"><select id="topic" aria-label="主题"><option value="">所有主题</option></select><select id="kind" aria-label="内容类型"><option value="">所有内容</option><option>综述与索引</option><option>逐篇笔记</option><option>研究专题</option><option>参考证据</option></select><div id="count" role="status"></div><div id="list"></div><div class="pager"><button id="prev">上一页</button><button id="next">下一页</button></div></aside><main><div id="navline"></div><article id="article"></article></main></div>
<script type="application/json" id="data">PAYLOAD</script>
<script>
const entries=JSON.parse(document.getElementById('data').textContent),byPath=new Map(entries.map(e=>[e.path,e]));
const q=document.getElementById('q'),topic=document.getElementById('topic'),kind=document.getElementById('kind'),list=document.getElementById('list'),count=document.getElementById('count'),article=document.getElementById('article');
let page=0,selected='README.md';
for(const t of [...new Set(entries.map(e=>e.topic))].sort()){const o=document.createElement('option');o.value=t;o.textContent=t==='总览'?t:t.slice(3);topic.append(o)}
function matches(){const words=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean),exactId=words.length===1&&/^[pb]\d{2,3}$/.test(words[0]);return entries.filter(e=>(!topic.value||e.topic===topic.value)&&(!kind.value||e.kind===kind.value)&&(exactId?(e.ids||[]).includes(words[0]):words.every(w=>e.search.includes(w))))}
function draw(){const found=matches();if(page*60>=found.length)page=0;count.textContent=`共 ${found.length} 项 · 显示 ${found.length?page*60+1:0}–${Math.min((page+1)*60,found.length)}`;list.replaceChildren();for(const e of found.slice(page*60,(page+1)*60)){const b=document.createElement('button');b.textContent=e.title;const s=document.createElement('small');s.textContent=(e.topic==='总览'?'总览':e.topic.slice(3))+' · '+e.kind;b.append(s);if(e.path===selected)b.className='active';b.onclick=()=>show(e.path);list.append(b)}document.getElementById('prev').disabled=page===0;document.getElementById('next').disabled=(page+1)*60>=found.length}
function show(path){const e=byPath.get(path)||byPath.get('README.md');selected=e.path;article.innerHTML=e.html;const nav=document.getElementById('navline');nav.replaceChildren();const label=document.createElement('span');label.textContent=(e.topic==='总览'?'总览':e.topic.slice(3))+' / '+e.kind;const source=document.createElement('a');source.href=e.path;source.textContent='打开源文件';nav.append(label,source);if(window.katex)for(const m of article.querySelectorAll('[data-math]')){katex.render(m.dataset.math,m,{displayMode:m.dataset.display==='true',throwOnError:false,strict:false,trust:false})}history.replaceState(null,'','#'+encodeURIComponent(e.path));draw();window.scrollTo({top:0,behavior:'auto'})}
for(const el of [q,topic,kind])el.addEventListener('input',()=>{page=0;draw()});
document.getElementById('prev').onclick=()=>{page--;draw()};document.getElementById('next').onclick=()=>{page++;draw()};
article.addEventListener('click',ev=>{const a=ev.target.closest('a');if(!a)return;if(a.dataset.local&&byPath.has(a.dataset.local)){ev.preventDefault();show(a.dataset.local)}else if(a.dataset.topic){ev.preventDefault();topic.value=a.dataset.topic;kind.value='逐篇笔记';q.value='';page=0;draw()}});
document.querySelector('[data-home]').onclick=e=>{e.preventDefault();show('README.md')};document.querySelector('[data-summary]').onclick=e=>{e.preventDefault();show('综合分析.md')};
window.addEventListener('hashchange',()=>show(decodeURIComponent(location.hash.slice(1))));
show(decodeURIComponent(location.hash.slice(1))||'README.md');
</script></body></html>'''
(ROOT/'阅读目录.html').write_text(template.replace('PAYLOAD',payload))
print(json.dumps({'entries':len(entries),'paper_notes':sum(e['kind']=='逐篇笔记' for e in entries),'bytes':(ROOT/'阅读目录.html').stat().st_size},ensure_ascii=False))
