/** Actual product route/viewport smoke evidence; detailed interactions are separate. */
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const base=process.argv[2]||'http://127.0.0.1:4173';
const out=path.resolve('artifacts/codex-browser/product');
await mkdir(out,{recursive:true});
const report={scope:'Claude product frontend, actual headless Chromium',base,startedAt:new Date().toISOString(),pages:[],screenshots:[],errors:[],externalRequests:[],limitations:['Emulated viewports, not physical phone','CSS 200% zoom is separately labelled; not toolbar zoom','Scientific validation is separate']};
const browser=await chromium.launch({headless:true});
async function ready(page) {
  // A hash navigation can finish before React's lazy view/data render. A
  // screenshot of Suspense's loading shell is not acceptance of that view.
  await page.waitForFunction(() => {
    const main = document.querySelector('main');
    return main?.querySelector('h1') && !main.querySelector('[role="status"]')
      && !/正在载入视图|正在校验并载入轨迹/.test(main.innerText);
  }, null, { timeout: 15000 });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}
try {
  const context=await browser.newContext({viewport:{width:1366,height:900}});
  const page=await context.newPage();
  page.on('pageerror',e=>report.errors.push({url:page.url(),message:e.message}));
  page.on('console',e=>{if(e.type()==='error')report.errors.push({url:page.url(),message:e.text()});});
  page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:')&&!r.url().startsWith('blob:'))report.externalRequests.push(r.url());});
  const catalogResponse=await page.request.get(base+'/data/catalog.json');
  if(catalogResponse.status()!==200)throw new Error('Real catalog unavailable');
  const catalog=await catalogResponse.json();
  const sample=catalog.streams.find(s=>s.split==='confirmation'&&s.family==='weibull_3_45'&&s.order==='descending');
  report.realSample=sample.instance_id;
  const routes=[['overview','#/'],['samples','#/samples'],['replay',`#/replay/${sample.instance_id}?t=500`],['risk','#/risk'],['evidence','#/evidence']];
  for(const [name,hash] of routes){
    await page.goto(base+'/'+hash,{waitUntil:'networkidle'});
    await ready(page);
    await page.locator('main').waitFor();
    const text=await page.locator('main').innerText();
    const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1}));
    if(!text.trim()||/Internal Server Error|Failed to resolve import/.test(text))throw new Error(`${name}: product did not render`);
    report.pages.push({name,url:page.url(),title:await page.title(),text,layout});
    const filename=`${name}-1366.png`;await page.screenshot({path:path.join(out,filename),fullPage:true});report.screenshots.push(filename);
    const viewportFile=`${name}-1366-viewport.png`;await page.screenshot({path:path.join(out,viewportFile)});report.screenshots.push(viewportFile);
  }
  for(const [width,height] of [[360,800],[390,844],[430,932],[844,390],[1920,1080],[900,1366]]){
    await page.setViewportSize({width,height});
    await page.goto(base+`/#/replay/${sample.instance_id}?t=500`,{waitUntil:'networkidle'});
    await ready(page);
    const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1}));
    report.pages.push({name:`replay-${width}x${height}`,layout,text:await page.locator('main').innerText()});
    const filename=`replay-${width}x${height}.png`;await page.screenshot({path:path.join(out,filename),fullPage:true});report.screenshots.push(filename);
    if(width<500){const viewportFile=`replay-${width}-viewport.png`;await page.screenshot({path:path.join(out,viewportFile)});report.screenshots.push(viewportFile);}
    if(width<500||width===1920){
      for(const [name,hash] of routes.filter(([name])=>name!=='replay')){
        await page.goto(base+'/'+hash,{waitUntil:'networkidle'});
        await ready(page);
        const otherLayout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1}));
        report.pages.push({name:`${name}-${width}x${height}`,layout:otherLayout,text:await page.locator('main').innerText()});
        const otherFile=`${name}-${width}x${height}.png`;await page.screenshot({path:path.join(out,otherFile),fullPage:true});report.screenshots.push(otherFile);
        if(width<500){const viewportFile=`${name}-${width}-viewport.png`;await page.screenshot({path:path.join(out,viewportFile)});report.screenshots.push(viewportFile);}
      }
    }
  }
  await page.setViewportSize({width:1366,height:900});
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto(base+`/#/replay/${sample.instance_id}?t=500`,{waitUntil:'networkidle'});
  await ready(page);
  await page.evaluate(()=>{document.documentElement.style.zoom='2';});
  report.pages.push({name:'replay-css-zoom-200-reduced-motion',acceptance:false,note:'Supplementary CSS diagnostic; true browser 200% zoom is separately checked with zoom-check.mjs',layout:await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,cssZoom:getComputedStyle(document.documentElement).zoom}))});
  await page.screenshot({path:path.join(out,'replay-css-zoom-200.png'),fullPage:true});report.screenshots.push('replay-css-zoom-200.png');
  report.status=report.errors.length||report.externalRequests.length||report.pages.some(p=>p.acceptance!==false&&p.layout.overflow)?'FAIL':'PASS';
} catch(e){report.status='FAIL';report.errors.push({message:e.stack});}
finally {report.finishedAt=new Date().toISOString();await writeFile(path.join(out,'visual-report.json'),JSON.stringify(report,null,2));await browser.close();}
console.log(JSON.stringify({status:report.status,pages:report.pages.length,errors:report.errors,externalRequests:report.externalRequests},null,2));
process.exitCode=report.status==='PASS'?0:1;
