/** Partial product acceptance while remaining views are under construction. */
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const base=process.argv[2]||'http://127.0.0.1:5173';
const out=path.resolve('artifacts/codex-browser/product-overview');await mkdir(out,{recursive:true});
const report={scope:'Product Overview only; other views excluded',startedAt:new Date().toISOString(),base,checks:[],consoleErrors:[],screenshots:[]};
const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1366,height:900}});
page.on('pageerror',e=>report.consoleErrors.push(e.message));page.on('console',m=>{if(m.type()==='error')report.consoleErrors.push(m.text());});
async function check(name,fn){try{const evidence=await fn();report.checks.push({name,status:'PASS',evidence});console.log('PASS',name);}catch(e){report.checks.push({name,status:'FAIL',error:e.message});console.log('FAIL',name,e.message);}}
await page.goto(base,{waitUntil:'networkidle'});
await check('real summary and runtime',async()=>{assert.match(await page.locator('h1').innerText(),/21.45/);assert.equal(report.consoleErrors.length,0);return {heading:await page.locator('h1').innerText(),errors:report.consoleErrors};});
await check('all108 stream points stay inside SVG',async()=>{
  const fig=page.locator('figure').filter({has:page.locator('figcaption').filter({hasText:'108 条确认流的选择器减训练'})});
  const geometry=await fig.locator('svg').evaluate(svg=>{const r=svg.getBoundingClientRect();const dots=[...svg.querySelectorAll('circle[role="button"]')].map(c=>{const p=c.getBoundingClientRect();return {label:c.getAttribute('aria-label'),top:p.top-r.top,bottom:p.bottom-r.top,left:p.left-r.left,right:p.right-r.left};});return {height:r.height,width:r.width,total:dots.length,clipped:dots.filter(p=>p.top<0||p.bottom>r.height||p.left<0||p.right>r.width)};});
  await writeFile(path.join(out,'distribution-geometry.json'),JSON.stringify(geometry,null,2));assert.equal(geometry.total,108);assert.equal(geometry.clipped.length,0,`${geometry.clipped.length} points clipped`);return geometry;
});
await check('headroom segment and readable marker labels',async()=>{
  const aside=page.locator('aside').filter({has:page.getByRole('heading',{name:/收回了可改善余地/})});
  const geometry=await aside.locator('svg[role="img"]').evaluate(svg=>{const lines=[...svg.querySelectorAll('line')].map(l=>({x1:+l.getAttribute('x1'),x2:+l.getAttribute('x2')}));const texts=[...svg.querySelectorAll('text')].filter(t=>['分支 oracle','SBS'].includes(t.textContent.trim())||t.textContent.trim().startsWith('选择器')).map(t=>{const r=t.getBoundingClientRect();return {label:t.textContent.trim(),left:r.left,right:r.right,top:r.top,bottom:r.bottom};});return {lines,texts};});
  await writeFile(path.join(out,'headroom-geometry.json'),JSON.stringify(geometry,null,2));assert.equal(geometry.lines[1].x2,geometry.lines[0].x2,'recovered segment should end at SBS');
  const [a,b]=geometry.texts;assert.ok(a.right<=b.left||b.right<=a.left||a.bottom<=b.top||b.bottom<=a.top,'oracle and selector labels overlap');assert.doesNotMatch(await aside.innerText(),/已收回（选择器\s*[−-]\s*SBS）/,'positive recovered bins must be labelled SBS minus selector');return geometry;
});
await check('evidence dialog keyboard trap and return focus',async()=>{
  const trigger=page.getByRole('button',{name:/查看.*出处与核验范围/}).first();const label=await trigger.getAttribute('aria-label');await trigger.click();const dialog=page.getByRole('dialog');await dialog.waitFor();
  assert.ok(await dialog.evaluate(d=>d.contains(document.activeElement)));await page.keyboard.press('Tab');assert.ok(await dialog.evaluate(d=>d.contains(document.activeElement)));await page.keyboard.press('Escape');await dialog.waitFor({state:'detached'});
  await page.waitForFunction(expected=>document.activeElement?.getAttribute('aria-label')===expected,label,{timeout:2000});
  assert.equal(await page.evaluate(()=>document.activeElement?.getAttribute('aria-label')),label,'Escape should restore focus to opening control');return {trigger:label};
});
await check('36039043013661920 widths and landscape',async()=>{
  const layouts=[];
  for(const [w,h]of [[360,800],[390,844],[430,932],[1366,900],[1920,1080],[844,390]]){await page.setViewportSize({width:w,height:h});await page.goto(base,{waitUntil:'networkidle'});const g=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,wideElements:[...document.querySelectorAll('main *')].map(e=>{const r=e.getBoundingClientRect();return {tag:e.tagName,className:e.getAttribute('class'),width:r.width,left:r.left,right:r.right};}).filter(e=>e.right>innerWidth+1&&e.width>innerWidth).slice(0,20)}));layouts.push(g);const file=`overview-${w}x${h}.png`;await page.screenshot({path:path.join(out,file),fullPage:true});report.screenshots.push(file);}
  await writeFile(path.join(out,'layout-geometry.json'),JSON.stringify(layouts,null,2));
  await page.setViewportSize({width:1366,height:900});await page.emulateMedia({reducedMotion:'reduce'});await page.evaluate(()=>document.documentElement.style.zoom='2');const zoom=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));await page.screenshot({path:path.join(out,'overview-css-zoom200.png'),fullPage:true});report.screenshots.push('overview-css-zoom200.png');assert.ok(layouts.every(g=>g.scrollWidth<=g.width+1),'viewport overflow: '+layouts.filter(g=>g.scrollWidth>g.width+1).map(g=>`${g.width}→${g.scrollWidth}`).join(','));return {layouts,physicalPhone:false,supplementaryCssZoomDiagnostic:zoom,browserZoomAcceptance:'Separate zoom-check.mjs uses actual Chrome tabs.setZoom(2), with responsive layout viewport; CSS zoom does not emulate that requirement'};
});
report.status=report.checks.every(c=>c.status==='PASS')?'PASS':'FAIL';report.finishedAt=new Date().toISOString();await writeFile(path.join(out,'overview-report.json'),JSON.stringify(report,null,2));await browser.close();console.log(JSON.stringify({status:report.status,checks:report.checks.map(c=>({name:c.name,status:c.status,error:c.error}))},null,2));process.exitCode=report.status==='PASS'?0:1;
