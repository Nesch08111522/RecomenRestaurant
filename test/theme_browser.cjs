const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{const file=path.join(root,decodeURIComponent(req.url.split('?')[0]));if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}try{const type={'.css':'text/css','.js':'text/javascript','.html':'text/html','.svg':'image/svg+xml','.webp':'image/webp'}[path.extname(file)];res.setHeader('Content-Type',type||'application/octet-stream');res.end(fs.readFileSync(file));}catch{res.writeHead(404).end();}});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const origin='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({...(process.env.THEME_BROWSER ? {executablePath:process.env.THEME_BROWSER} : {channel:'msedge'}),headless:true});
 const results=[];
 try {
  for(const fixture of (process.env.THEME_FIXTURES || 'admin,public,editor,analytics,categories,users,restaurant-form,catalog,login,register,market,menu').split(',')){
   const context=await browser.newContext({colorScheme:'light',reducedMotion:'reduce',viewport:{width:1440,height:1000}});
   const page=await context.newPage();
   await page.goto(origin+'/outputs/theme-qa/'+fixture+'.html');
   assert.equal(await page.locator('html').getAttribute('data-theme'),'dark','OS light must not override default');
   for(const theme of ['dark','light']){
    if(theme==='light')await page.locator('[data-theme-toggle]').first().click();
    assert.equal(await page.locator('html').getAttribute('data-theme'),theme);
    await page.reload();
    assert.equal(await page.locator('html').getAttribute('data-theme'),theme);
    await page.screenshot({path:root+'/outputs/theme-qa/'+fixture+'-'+theme+'.png',fullPage:true});
    const contrast=await page.evaluate(()=>{
      const rgb=s=>{const c=(s.match(/[\d.]+/g)||[]).map(Number);return s.startsWith('color(srgb')?c.map((v,i)=>i<3?v*255:v):c;};
      const lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((v,x,i)=>v+x*[.2126,.7152,.0722][i],0);
      const out=[];
      for(const e of document.querySelectorAll('body *')){
       if(![...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())||!e.getClientRects().length||['SCRIPT','STYLE','OPTION'].includes(e.tagName))continue;
       const cs=getComputedStyle(e);if(cs.visibility==='hidden'||cs.display==='none')continue;
       let bg,el=e;
       while(el){const c=rgb(getComputedStyle(el).backgroundColor);if(c.length===3||c[3]>.95){bg=c;break;}el=el.parentElement;}
       if(!bg)continue;
       let opacity=1;for(let parent=e;parent;parent=parent.parentElement)opacity*=Number(getComputedStyle(parent).opacity);
       if(opacity===0)continue;
       let fg=rgb(cs.color);opacity*=fg[3]??1;fg=fg.slice(0,3).map((v,i)=>v*opacity+bg[i]*(1-opacity));
       const l1=lum(fg),l2=lum(bg),ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
       if(ratio<4.5)out.push({tag:e.tagName,cls:e.className,text:e.textContent.trim().slice(0,45),ratio:Number(ratio.toFixed(2)),fg:cs.color,bg});
      }
      return out;
    });
    results.push({fixture,theme,contrastFailures:contrast});
    await page.setViewportSize({width:375,height:850});
    results.at(-1).mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    if(results.at(-1).mobileOverflow>0)console.log(fixture,await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1&&e.getBoundingClientRect().width>0).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})).slice(0,15)));
    await page.setViewportSize({width:1440,height:1000});
   }
   // Native button keyboard support and storage failures must not break switching.
   await page.locator('[data-theme-toggle]').first().focus();await page.keyboard.press('Space');
   assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
   await context.close();
  }
  const context=await browser.newContext();
  await context.addInitScript(()=>{Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked');}});});
  const page=await context.newPage();await page.goto(origin+'/outputs/theme-qa/public.html');
  assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
  await page.locator('[data-theme-toggle]').click();assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
  await context.close();
  fs.writeFileSync(root+'/outputs/theme-qa/results.json',JSON.stringify(results,null,2));
  assert.equal(results.reduce((n,r)=>n+r.contrastFailures.length,0),0,'Visible text must pass AA in rendered fixtures');
  console.log(JSON.stringify(results,null,2));
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
