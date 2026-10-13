import { ReplayDataClient, fetchJSON } from '/core/data-client.mjs';

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const esc = (x) => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (n, d=0) => n == null ? '—' : Number(n).toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d});
const familyNames = {weibull_3_45:'威布尔分布',uniform_1_100:'均匀分布',small_beta_2_5:'小物品 Beta',large_beta_5_2:'大物品 Beta',normal_50_15:'正态分布',bimodal_20_30_70_80:'双峰分布'};
const orderNames = {random:'随机到达',ascending:'升序到达',descending:'降序到达'};
const splitNames = {train:'训练集',confirmation:'确认集',risk:'构造风险集'};
const fam = x => familyNames[x] || x;
const ord = x => orderNames[x] || x;
let meta, streams=[], cells=[], comparison=null, selected=null, decision=null, loadVersion=0, playing=null, tab='overview';
let pageOffset={left:0,right:0}, selectedBins={left:null,right:null};
const client = new ReplayDataClient();
const params = new URLSearchParams(location.search);
const notice = (message, error=false) => {$('#notice').textContent=message;$('#notice').classList.toggle('error',error);};
const sourceHTML = (s) => s ? `<div class="source"><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.path)} ↗</a><code>SHA256 ${esc(s.sha256)}</code></div>` : '';
const kpi = (label,value,unit,note) => `<article class="card kpi"><div class="label">${label}</div><div class="number">${value}<small>${unit}</small></div><p>${note}</p></article>`;
function saveURL() {
  const p=new URLSearchParams();p.set('view',tab);
  for(const key of ['split','family','order','search','instance','left-policy','right-policy']) {if($('#'+key)?.value)p.set(key,$('#'+key).value);}
  if(comparison)p.set('t',String(comparison.processed));
  if($('#retrospective')?.checked)p.set('after','1');
  history.replaceState(null,'',`${location.pathname}?${p}`);
}
function setTab(name) {if(!['overview','replay','risk','evidence'].includes(name))name='overview';tab=name;pause();$$('.view').forEach(s=>s.hidden=s.id!==name);$$('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===name);b.setAttribute('aria-current',b.dataset.tab===name?'page':'false');});saveURL();}
function buildOverview(){
  const c=meta.summary.confirmation;
  $('#overview').innerHTML=`<p class="eyebrow">EXPERIMENT / FROZEN RESULTS</p><h1>选择的价值，从真实记录开始。</h1><p class="sub">用 500 项 BF 前缀，在两种固定策略间做一次选择。这里浏览的是已完成实验：每个数字、每次放置和每个决策，都可追溯至原始文件。</p><div class="kpis">${kpi('确认集 · SELECTOR − SBS',num(c.selector_minus_SBS_mean,2),'箱','负值表示节省箱数；108 条输入流')}${kpi('胜 / 平 / 负',c.W_T_L_vs_SBS.join(' / '),'','相对训练选出的基线 BF_then_EoH')}${kpi('可改善余地收回比例',num(c.headroom_recovered_fraction*100,2),'%','同 BF 前缀两分支事后 oracle 参照')}${kpi('真实记录',num(meta.counts.runs),'次运行',`${meta.counts.streams} 条输入流 · 每流 5000 项`)}</div>
  <div class="two"><article class="card"><h2>确认集中的平均箱数</h2><p class="muted small">完整历史结果 · 越少越好 · 相同输入流逐一配对</p>${['BF','BF_then_EoH','published_EoH','SELECTOR','branch_oracle'].map(p=>`<div class="bar-row ${p==='SELECTOR'?'highlight':''}"><span>${p==='branch_oracle'?'分支事后 oracle':p}</span><div class="bar"><b style="width:${c.mean_bins[p]/Math.max(...Object.values(c.mean_bins))*100}%"></b></div><span>${num(c.mean_bins[p],2)}</span></div>`).join('')}<p class="small muted">柱长从 0 起。published_EoH 从第 1 项采用 EoH，起始状态不同。SBS 是 BF_then_EoH 的基线角色，不是额外运行。</p></article>
  <article class="card"><h2>先观察，再选择</h2><div class="flow"><span>BF 前缀 500 项</span>→<span>31 维特征</span>→<span>5 个训练邻居</span>→<span>选择一次</span></div><div class="callout">组 bootstrap 95% 区间<br><strong>[${num(c.cluster_bootstrap_95_percentile_CI[0],2)}, ${num(c.cluster_bootstrap_95_percentile_CI[1],2)}] 箱</strong><br>同多重集的三种顺序共同抽样，仅描述本次预设合成混合。</div><button class="primary" id="start-replay">打开真实样本回放 →</button><p class="small muted">默认显示当时已知的信息，未来曲线与最终结果可在事后对照模式中查看。</p></article></div>
  <article class="card"><h2>六个尺寸族 × 三种到达顺序</h2><p class="muted small">18 个确认单元；点击“查看样本”联动筛选。不对局部筛选套用全局置信区间。</p><div class="table-wrap"><table><thead><tr><th>尺寸族</th><th>到达顺序</th><th>流数</th><th>平均差值 / 箱</th><th>胜 / 平 / 负</th><th></th></tr></thead><tbody>${cells.map(c=>`<tr><td>${fam(c.family)}</td><td>${ord(c.order)}</td><td>${c.n}</td><td class="${c.selector_minus_SBS<=0?'positive':'negative'}">${num(c.selector_minus_SBS,2)}</td><td>${c.wins} / ${c.ties} / ${c.losses}</td><td><button data-cell="${c.family}|${c.order}">查看样本</button></td></tr>`).join('')}</tbody></table></div></article>`;
  $('#start-replay').onclick=()=>setTab('replay');
  $$('[data-cell]').forEach(b=>b.onclick=()=>{const [f,o]=b.dataset.cell.split('|');$('#split').value='confirmation';$('#family').value=f;$('#order').value=o;$('#search').value='';filterStreams();setTab('replay');});
}
function buildReplay(){
  $('#replay').innerHTML=`<h1>样本与回放</h1><p class="sub">按记录恢复每一步。左右使用同一条输入流与同一时间，箱号保持原始槽位关系。</p><article class="card"><div class="filters"><label>数据分区<select id="split"><option value="confirmation">确认集 · 108 流</option><option value="train">训练集 · 144 流</option><option value="risk">构造风险集 · 12 流</option></select></label><label>尺寸族<select id="family"><option value="">全部尺寸族</option>${meta.protocol.families.map(f=>`<option value="${f}">${fam(f)}</option>`).join('')}</select></label><label>到达顺序<select id="order"><option value="">全部顺序</option>${[...new Set(streams.map(s=>s.order))].map(o=>`<option value="${esc(o)}">${esc(ord(o))}</option>`).join('')}</select></label><label>搜索记录 ID<input id="search" type="search" placeholder="输入流 / 多重集组"></label><label class="wide">真实输入流<select id="instance"></select></label><label>左侧策略<select id="left-policy"></select></label><label>右侧策略<select id="right-policy"></select></label></div><p id="filter-stats" class="small muted"></p><p id="replay-loading" class="small" role="status"></p></article>
  <article class="card play-card section-gap"><div class="runhead"><div class="time-readout"><span id="processed">0</span> <small>/ 5000 项已处理</small></div><label class="toggle"><input id="retrospective" type="checkbox">事后对照 · 展开未来曲线与结果</label></div><input id="timeline" class="timeline" type="range" min="0" max="5000" step="1" value="0" aria-label="已处理项数"><div class="controls"><button id="play" class="primary">▶ 播放</button><button id="step">下一项</button><button id="reset">重置</button>${[0,499,500,501,5000].map(n=>`<button data-seek="${n}">${n}</button>`).join('')}<label>播放速度<select id="speed"><option value="1">1× · 10项/秒</option><option value="5">5× · 50项/秒</option><option value="20">20× · 200项/秒</option><option value="100">100× · 1000项/秒</option></select></label></div><p id="mode-note" class="small muted"></p><p id="current-item" class="small"></p></article>
  <div class="two equal">${['left','right'].map(side=>`<article class="card"><div class="runhead"><h2 id="${side}-title">—</h2><span class="tag">同输入 · 同步时间</span></div><div id="${side}-stats" class="statline"></div><div class="controls"><button data-page="${side}|-1" aria-label="${side==='left'?'左':'右'}侧前一页箱">←</button><span id="${side}-page" class="small muted"></span><button data-page="${side}|1" aria-label="${side==='left'?'左':'右'}侧后一页箱">→</button><button data-active="${side}">定位当前箱</button></div><div id="${side}-bins" class="bins" aria-label="${side==='left'?'左':'右'}策略已使用箱"></div><div id="${side}-detail" class="bin-detail"></div></article>`).join('')}</div><article class="card"><h2>累计使用箱数</h2><div class="legend"><span id="legend-left">左侧</span><span id="legend-right">右侧（虚线）</span></div><svg id="curve" class="curve" role="img" aria-label="累计箱数与已处理项数曲线" viewBox="0 0 1000 180" preserveAspectRatio="none"></svg><p id="curve-text" class="small muted"></p></article><article id="decision" class="card section-gap"></article><article class="card section-gap"><h2>当前样本的证据</h2><div id="sample-sources"></div></article>`;
  for(const key of ['split','family','order','search']){if(params.has(key))$('#'+key).value=params.get(key);$('#'+key).addEventListener(key==='search'?'input':'change',()=>filterStreams());}
  if(!$('#split').value)$('#split').value='confirmation';
  $('#instance').onchange=()=>{setPolicies();loadRun();};
  $('#left-policy').onchange=()=>loadRun();$('#right-policy').onchange=()=>loadRun();
  $('#retrospective').checked=params.get('after')==='1';$('#retrospective').onchange=()=>{renderReplay();saveURL();};
  $('#timeline').oninput=e=>{pause();seek(+e.target.value);};
  $$('[data-seek]').forEach(b=>b.onclick=()=>{pause();seek(+b.dataset.seek);});
  $('#step').onclick=()=>{pause();seek(Math.min(5000,(comparison?.processed||0)+1));};$('#reset').onclick=()=>{pause();seek(0);};
  $('#play').onclick=()=>{if(playing){pause();return;}if(!comparison)return;if(comparison.processed===5000)seek(0);$('#play').textContent='Ⅱ 暂停';playing=setInterval(()=>{if(!comparison)return pause();const t=Math.min(5000,comparison.processed+(+$('#speed').value));seek(t);if(t===5000)pause();},100);};
  $$('[data-page]').forEach(b=>b.onclick=()=>{const [s,d]=b.dataset.page.split('|');pageOffset[s]=Math.max(0,pageOffset[s]+Number(d)*80);renderBins(s);});
  $$('[data-active]').forEach(b=>b.onclick=()=>{const s=b.dataset.active;if(!comparison)return;const st=comparison.getState()[s];selectedBins[s]=st.activeBin;const all=comparison.getBins(s,{limit:5000}).bins;pageOffset[s]=Math.floor(Math.max(0,all.findIndex(x=>x.bin===st.activeBin))/80)*80;renderBins(s);});
  filterStreams(params.get('instance'),true);
}
function pause(){if(playing){clearInterval(playing);playing=null;}if($('#play'))$('#play').textContent='▶ 播放';}
function filterStreams(preferred=null,initial=false){
  pause();const split=$('#split').value, f=$('#family').value,o=$('#order').value,q=$('#search').value.toLowerCase();
  const matches=streams.filter(s=>s.split===split&&(!f||s.family===f)&&(!o||s.order===o)&&(!q||(s.instance_id+' '+s.group_id).toLowerCase().includes(q)));
  const previous=preferred||$('#instance').value;
  $('#instance').innerHTML=matches.map(s=>`<option value="${esc(s.instance_id)}">${esc(fam(s.family))} · ${esc(ord(s.order))} · ${esc(s.instance_id)}</option>`).join('');
  if(matches.some(s=>s.instance_id===previous))$('#instance').value=previous;
  const deltas=matches.map(s=>s.results.selector_minus_SBS).filter(Number.isFinite);
  $('#filter-stats').textContent=`当前筛选 ${matches.length} 条流 / ${new Set(matches.map(s=>s.group_id)).size} 个多重集或前缀组${deltas.length?' · 历史筛选均值 SELECTOR − SBS '+num(deltas.reduce((a,b)=>a+b,0)/deltas.length,2)+' 箱（未计算局部区间）':' · 训练集没有 SELECTOR 运行'}`;
  setPolicies(initial);loadRun(initial?Number(params.get('t')||0):0);saveURL();
}
function setPolicies(initial=false){
  selected=streams.find(s=>s.instance_id===$('#instance').value)||null;
  for(const side of ['left','right']){const select=$('#'+side+'-policy');const prev=initial?params.get(side+'-policy'):select.value;select.innerHTML=(selected?.runs||[]).map(r=>`<option value="${r.policy}">${r.policy}</option>`).join('');select.value=(selected?.runs||[]).some(r=>r.policy===prev)?prev:side==='left'?(selected?.runs.some(r=>r.policy==='SELECTOR')?'SELECTOR':'BF'):'BF_then_EoH';}
}
async function loadRun(processed=0){
  pause();const version=++loadVersion;comparison=null;decision=null;pageOffset={left:0,right:0};selectedBins={left:null,right:null};client.cancel();
  renderReplay();if(!selected){$('#replay-loading').textContent='没有符合条件的真实样本，请调整筛选。';saveURL();return;}
  const stream=selected;$('#replay-loading').textContent='正在读取两条轨迹并校验 SHA256…';
  $('#sample-sources').innerHTML=sourceHTML(stream.source)+stream.runs.filter(r=>[$('#left-policy').value,$('#right-policy').value].includes(r.policy)).map(r=>sourceHTML(r.source.record)+sourceHTML(r.source.trajectory)).join('');
  try{
    const left=stream.runs.find(r=>r.policy===$('#left-policy').value),right=stream.runs.find(r=>r.policy===$('#right-policy').value);
    const [engine,dec]=await Promise.all([client.loadComparison(left,right,{processed:Number.isInteger(processed)?Math.min(5000,Math.max(0,processed)):0}),stream.decision_url?fetchJSON(stream.decision_url):null]);
    if(version!==loadVersion)return;comparison=engine;decision=dec;$('#replay-loading').textContent=`两条轨迹 SHA256 已核对 · ${stream.instance_id}`;renderReplay();saveURL();
  }catch(e){if(version!==loadVersion||e.name==='StaleResponseError'||e.name==='AbortError')return;comparison=null;$('#replay-loading').innerHTML=`加载失败：${esc(e.message)} <button id="retry">重试</button>`;$('#retry').onclick=()=>loadRun();renderReplay();}
}
function seek(t){if(!comparison)return;try{comparison.seek(t);renderReplay();saveURL();}catch(e){pause();notice('轨迹校验失败：'+e.message,true);}}
function renderReplay(){
  const retrospective=$('#retrospective').checked,t=comparison?.processed||0;$('#processed').textContent=num(t);$('#timeline').value=t;
  $('#timeline').disabled=!comparison;for(const id of ['play','step','reset'])$('#'+id).disabled=!comparison;
  $$('[data-seek]').forEach(b=>b.disabled=!comparison);
  $('#mode-note').textContent=retrospective?'事后对照：完整曲线和已发生的最终结果可见；决策仍来自冻结历史记录。':'当时已知：只展示已经到达的物品与曲线。第 500 项处理完、第 501 项尚未到达时展示选择。';
  const state=comparison?.getState({retrospective});
  $('#current-item').textContent=state?.left.current?`第 ${t} 项 · 大小 ${state.left.current.size} · 左侧放入箱 #${state.left.current.bin+1}，残量 ${state.left.current.before} → ${state.left.current.after}；右侧放入箱 #${state.right.current.bin+1}，残量 ${state.right.current.before} → ${state.right.current.after}。`:'初态：还没有物品到达，也没有使用任何箱。';
  for(const side of ['left','right']){const s=state?.[side];$('#'+side+'-title').textContent=s?.policy||'等待真实轨迹';$('#'+side+'-stats').innerHTML=s?`<span><strong>${num(s.usedBins)}</strong><small>已用箱</small></span><span><strong>${num(s.unusedCapacity)}</strong><small>已用箱总残量</small></span>`:'';renderBins(side);}
  renderCurve();renderDecision();
}
function renderBins(side){
  const box=$('#'+side+'-bins'),detail=$('#'+side+'-detail');if(!comparison){box.innerHTML='';detail.textContent='未加载轨迹';$('#'+side+'-page').textContent='';return;}
  const state=comparison.getState()[side];if(pageOffset[side]>=state.usedBins)pageOffset[side]=Math.max(0,Math.floor((state.usedBins-1)/80)*80);
  const view=comparison.getBins(side,{offset:pageOffset[side],limit:80});
  if(selectedBins[side]==null||!comparison.getBin(side,selectedBins[side]).used)selectedBins[side]=state.activeBin;
  box.innerHTML=view.bins.map(b=>`<button class="bin ${b.active?'active':''} ${b.bin===selectedBins[side]?'selected':''}" style="--load:${b.load}%" data-bin="${side}|${b.bin}" aria-label="箱 ${b.bin+1}，${b.count}项，剩余${b.remaining}"><span>${b.bin+1}</span></button>`).join('');
  $('#'+side+'-page').textContent=view.total?`${pageOffset[side]+1}–${Math.min(pageOffset[side]+80,view.total)} / ${view.total} 个已用箱`:'尚无已用箱';
  $$(`[data-bin^="${side}|"]`).forEach(b=>b.onclick=()=>{selectedBins[side]=+b.dataset.bin.split('|')[1];renderBins(side);});
  if(selectedBins[side]!=null){const b=comparison.getBin(side,selectedBins[side]);detail.textContent=`箱 #${b.bin+1} · ${b.count} 项 · 已装 ${b.load}/100 · 剩余 ${b.remaining}。物品：${b.items.map(i=>`第${i.itemNumber}项(${i.size})`).join('、')}`;}else detail.textContent='橙色框标记当前物品放入的箱；点击任意箱可查看已到达物品。';
}
function renderCurve(){
  const svg=$('#curve');if(!comparison){svg.innerHTML='';$('#curve-text').textContent='';return;}
  const opts={retrospective:$('#retrospective').checked},left=comparison.getCurve('left',opts),right=comparison.getCurve('right',opts),end=left.at(-1).processed;
  const ymax=Math.max(1,left.at(-1).usedBins,right.at(-1).usedBins);const path=points=>points.filter((p,i)=>i%Math.max(1,Math.floor(points.length/400))===0||i===points.length-1).map((p,i)=>`${i?'L':'M'}${40+p.processed/5000*940},${145-p.usedBins/ymax*125}`).join(' ');
  svg.innerHTML=`<line x1="40" x2="980" y1="145" y2="145" stroke="#d8e2da"/><line x1="40" x2="40" y1="20" y2="145" stroke="#d8e2da"/><text x="5" y="25">${ymax}</text><text x="20" y="149">0</text><text x="40" y="172">0项</text><text x="900" y="172">5000项</text><path d="${path(left)}" fill="none" stroke="#087f75" stroke-width="2"/><path d="${path(right)}" fill="none" stroke="#b67839" stroke-width="2" stroke-dasharray="5 4"/>`;
  const state=comparison.getState();$('#legend-left').textContent='左：'+state.left.policy;$('#legend-right').textContent='右：'+state.right.policy+'（虚线）';
  $('#curve-text').textContent=`曲线显示至第 ${end} 项；当前第 ${state.processed} 项，左 ${state.left.usedBins} 箱，右 ${state.right.usedBins} 箱，差 ${state.deltaUsedBins} 箱。${opts.retrospective?'最终左 '+left.at(-1).usedBins+' 箱，右 '+right.at(-1).usedBins+' 箱。':'曲线不包含未来结果。'}`;
}
function renderDecision(){
  const box=$('#decision');if(!comparison){box.innerHTML='<h2>第 500 项后的选择</h2><div class="empty">等待真实样本</div>';return;}
  if(!decision){box.innerHTML='<h2>第 500 项后的选择</h2><p class="muted">训练集只含两个实际分支运行，没有 SELECTOR 决策记录。</p>';return;}
  if(comparison.processed<500&&!$('#retrospective').checked){box.innerHTML='<h2>第 500 项后的选择</h2><div class="empty">尚未到达选择时刻。前 500 项统一使用 BF，当前不展示选择与邻居。</div>';return;}
  const d=decision,branch=meta.protocol.branches[d.selected_index];
  box.innerHTML=`<div class="runhead"><h2>500 项已处理 · 选择 ${esc(branch)}</h2><span class="tag">一次选择 · 冻结 k = ${meta.model.k}</span></div><p class="muted small">31 维前缀特征经训练集均值和标准差归一化，寻找 5 个训练邻居，平均两分支标签作为最终箱数预测。平方距离不是概率或置信度。</p><div class="decision-grid">${d.predicted_final_bins.map((n,i)=>`<div class="prediction ${i===d.selected_index?'chosen':''}">${meta.protocol.branches[i]}${i===d.selected_index?' · ✓ 选中':''}<strong>${num(n,1)} <small>箱</small></strong><span class="small muted">训练邻居预测值</span></div>`).join('')}</div><div class="table-wrap"><table><thead><tr><th>训练行索引（0基）</th><th>真实训练邻居</th><th>平方距离</th><th>BF / BF_then_EoH 标签</th></tr></thead><tbody>${d.neighbor_rows.map(n=>`<tr><td>${n.index}</td><td><button class="link" data-neighbor="${esc(n.instance_id)}">${esc(n.instance_id)}</button></td><td>${num(n.squared_distance,6)}</td><td>${n.labels.join(' / ')}</td></tr>`).join('')}</tbody></table></div><details><summary>展开全部 31 维前缀特征（协议原始顺序）</summary><div class="table-wrap"><table><thead><tr><th>维度</th><th>协议特征名</th><th>值（已按协议归一化）</th></tr></thead><tbody>${d.features.map((x,i)=>`<tr><td>${i+1}</td><td>${esc(d.feature_names[i])}</td><td>${num(x,8)}</td></tr>`).join('')}</tbody></table></div></details>${sourceHTML(d.source.model)}${sourceHTML(d.source.freeze)}`;
  $$('[data-neighbor]').forEach(b=>b.onclick=()=>openStream(b.dataset.neighbor));
}
function openStream(id,t=500){const s=streams.find(s=>s.instance_id===id);if(!s)return;$('#split').value=s.split;$('#family').value='';$('#order').value='';$('#search').value='';filterStreams(id);setTab('replay');loadRun(t);}
function buildRisk(){const r=meta.summary.risk.summary;$('#risk').innerHTML=`<h1>收益与风险，要分开看。</h1><p class="sub">确认集描述预设合成混合中的收益；构造风险集追问：前缀完全相同、未来改变后，同一个选择会付出什么代价？</p><div class="kpis">${kpi('风险集 · SELECTOR − SBS','+'+num(r.selector_minus_SBS_mean,2),'箱','12 条构造流，单独汇总')}${kpi('最坏分支事后后悔',num(Math.max(...streams.filter(s=>s.split==='risk').map(s=>s.results.selector_regret))),'箱','SELECTOR 相对同前缀分支 oracle')}${kpi('相同前缀组',meta.summary.risk.groups.length,'组','每组 3 种不同的未来')}${kpi('胜 / 平 / 负',r.W_T_L_vs_SBS.join(' / '),'','相对训练选出的 SBS')}</div><div class="callout warn">风险集不是确认集的额外样本。前缀信息不能识别任意未来；同样的观察可导向不同的最优后续策略。不要把这里的损失并入确认收益，也不要把余地收回比例解释为总体装箱效率。</div>${meta.summary.risk.groups.map(g=>`<article class="card risk-group"><div class="section-title"><h2>${esc(g.group.replace('risk_prefix_',''))}</h2><span class="tag">同前缀 · 相同选择 ${g.choice}</span></div><div class="table-wrap"><table><thead><tr><th>不同未来</th><th>BF</th><th>BF→EoH</th><th>SELECTOR</th><th>事后后悔</th><th></th></tr></thead><tbody>${streams.filter(s=>s.group_id===g.group).map(s=>`<tr><td>${esc(s.instance_id.split('__').at(-1))}</td><td>${s.results.BF}</td><td>${s.results.BF_then_EoH}</td><td>${s.results.SELECTOR}</td><td class="${s.results.selector_regret?'negative':''}">${s.results.selector_regret} 箱</td><td><button data-risk="${esc(s.instance_id)}">在第500项回放</button></td></tr>`).join('')}</tbody></table></div><p class="muted small">${g.oracle_preference_reverses?'不同未来中，严格最优分支发生反转。':'此组未出现两个方向的严格最优分支反转，仍保留实际平局和后悔值。'}</p></article>`).join('')}`;$$('[data-risk]').forEach(b=>b.onclick=()=>openStream(b.dataset.risk));}
function buildEvidence(){const v=meta.project_validation;$('#evidence').innerHTML=`<h1>证据链，止于原始字节。</h1><p class="sub">区分原实验的历史审计、本项目新做的数据核验，以及实际浏览器和迁移验收。所有来源文件保留 SHA256，可下载核对。</p><div class="two equal"><article class="card"><h2>本项目数据核验</h2><span class="tag">${esc(v.status)}</span><p>导入：${meta.import_validation.manifest_entries} / ${meta.import_validation.manifest_entries} 清单文件哈希一致。ZIP ${meta.import_validation.zip_members} 个成员，差异为 MANIFEST 自身。</p><pre class="small" style="white-space:pre-wrap;overflow-wrap:anywhere">${esc(JSON.stringify(v.coverage||{说明:'独立全量科学验证尚在进行'},null,2))}</pre><a href="/data/validation.json" target="_blank">读取本项目完整核验报告 ↗</a></article><article class="card"><h2>包内历史独立审计</h2><p><strong>${esc(meta.historical_audit.scientific_result_status)}</strong></p><p>科学数据与预定分析通过；保留验证器中断、缓存版重新验证及文档修复说明。</p><div class="callout warn">整个历史任务的 900 CPU 秒预算无法认证（NOT_ESTABLISHED）。历史 PASS 不表示这个应用已通过验收。</div><p class="small muted">本界面是独立数据验收入口；真实手机、原生 Ubuntu、跨平台浮点等未验证范围以交付记录为准。视觉参考图未查看。</p></article></div><article class="card"><h2>研究文件与分析依据</h2>${Object.values(meta.sources).map(sourceHTML).join('')}</article>`;}
async function main(){try{[meta,{streams},{cells}]=await Promise.all([fetchJSON('/data/meta.json'),fetchJSON('/data/catalog.json'),fetchJSON('/data/cells.json')]);if(meta.schema_version!==1||!Array.isArray(streams)||!Array.isArray(cells))throw new Error('不支持的数据接口版本');buildReplay();buildOverview();buildRisk();buildEvidence();$$('[data-tab]').forEach(b=>b.onclick=()=>setTab(b.dataset.tab));$('.brand').onclick=e=>{e.preventDefault();setTab('overview');};setTab(params.get('view')||'overview');notice(`冻结实验 · ${meta.counts.streams} 条流 / ${meta.counts.runs} 次运行 · 本项目数据核验 ${meta.project_validation.status}`);}catch(e){notice('无法载入实验数据：'+e.message+'。请先执行数据转换，再刷新页面。',true);}}
window.addEventListener('pagehide',pause);
main();
