/* Run via test/visual_server.py with Playwright and a disposable PostgreSQL database. */
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
    const browser = await chromium.launch({executablePath: process.env.EDGE_PATH || undefined,args:['--disable-gpu','--disable-background-timer-throttling']});
    const results = [];
    const output = process.env.VISUAL_OUTPUT;
    fs.mkdirSync(output, {recursive:true});
    try {
        for (const [role, route] of Object.entries({public:'/', user:'/mercado/', business_owner:'/owner/dashboard', admin:'/admin/dashboard'})) {
            const context = await browser.newContext({reducedMotion:'reduce', locale:'es-PE'});
            const page = await context.newPage();
            const origin = process.env.VISUAL_ORIGIN;
            await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
            await page.addInitScript(() => {
                window.vitals = {lcp:null, cls:0, interaction:null};
                new PerformanceObserver(list => { for(const e of list.getEntries()) window.vitals.lcp = e.startTime; }).observe({type:'largest-contentful-paint', buffered:true});
                new PerformanceObserver(list => { for(const e of list.getEntries()) if(!e.hadRecentInput) window.vitals.cls += e.value; }).observe({type:'layout-shift', buffered:true});
                new PerformanceObserver(list => { for(const e of list.getEntries()) if(e.interactionId) window.vitals.interaction = Math.max(window.vitals.interaction || 0,e.duration); }).observe({type:'event', durationThreshold:16, buffered:true});
            });
            if(role !== 'public') {
                await page.goto(origin+'/auth/login');
                await page.locator('[data-pane="login"] [name=username]').fill(process.env.VISUAL_PREFIX+role);
                await page.locator('[data-pane="login"] [name=password]').fill(process.env.VISUAL_PASSWORD);
                await Promise.all([page.waitForURL(url => !url.pathname.endsWith('/login')),page.locator('[data-pane="login"] button[type=submit].auth-btn').click()]);
            }
            for(const width of [360,768,1024,1366,1440,1920,2560]) {
                await page.setViewportSize({width,height:850});
                const res = await page.goto(origin+route);
                assert.equal(res.status(),200,role+' '+route);
                await page.evaluate(() => document.fonts.ready);
                await page.waitForTimeout(250);
                for(const theme of ['light','dark']) {
                    if(await page.locator('html').getAttribute('data-theme') !== theme) await page.locator('#themeToggle').click();
                    assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
                    await page.waitForTimeout(150);
                    const overflow = await page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth);
                    results.push({role,width,theme,overflow,...await page.evaluate(() => window.vitals)});
                    if([360,1366,1920,2560].includes(width)) {
                        const cdp = await context.newCDPSession(page);
                        const shot = await cdp.send('Page.captureScreenshot', {format:'png',fromSurface:true,captureBeyondViewport:false});
                        const png = Buffer.from(shot.data,'base64');
                        await cdp.detach();
                        const file = path.join(output,role+'-'+width+'-'+theme+'.png');
                        if(process.env.VISUAL_COMPARE === '1') assert.ok(png.equals(fs.readFileSync(path.join(process.env.VISUAL_BASELINE || output,path.basename(file)))), 'Cambio visual: '+file);
                        else fs.writeFileSync(file,png);
                    }
                }
            }
            if(role === 'business_owner') {
                const publicPath = await page.locator('#mgr-share').getAttribute('data-public');
                await context.grantPermissions(['clipboard-read','clipboard-write'],{origin});
                await page.evaluate(() => Object.defineProperty(navigator,'share',{configurable:true,value:undefined}));
                await page.locator('#mgr-share').click();
                await page.getByText('Enlace copiado.').waitFor();
                assert.equal(await page.evaluate(() => navigator.clipboard.readText()),origin+publicPath);
                assert.equal((await page.goto(origin+publicPath)).status(),200);
            }
            await page.setViewportSize({width:360,height:850});
            await page.locator('.sr-menu-button').click();
            assert.equal(await page.locator('#sr-navigation').getAttribute('aria-modal'),'true');
            await page.keyboard.press('Escape');
            assert.equal(await page.locator('.sr-menu-button').getAttribute('aria-expanded'),'false');
            await page.setViewportSize({width:1440,height:850});
            const rail = page.locator('#sr-navigation');
            assert.equal(await rail.evaluate(el => el.offsetWidth),70);
            await page.locator('.sr-collapse').click();
            assert.ok(await rail.evaluate(el => el.offsetWidth) > 150);
            await page.reload();
            assert.equal(await rail.evaluate(el => el.offsetWidth),70);
            if (role === 'public') {
                await page.evaluate(() => {
                    window.geoReads = 0;
                    Object.defineProperty(navigator,'geolocation',{configurable:true,value:{
                        getCurrentPosition(done) {
                            window.geoReads++;
                            setTimeout(() => done({coords:{latitude:0,longitude:0,accuracy:10}}),100);
                        }
                    }});
                });
                await page.locator('#locationBtn').click();
                await page.evaluate(() => window.app.getUserLocation());
                await page.waitForFunction(() => document.querySelector('#geo-status').textContent === 'Ubicación encontrada.');
                assert.equal(await page.evaluate(() => window.geoReads),1);
            }
            await page.reload();
            assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
            await context.close();
        }
        fs.writeFileSync(path.join(output,'mediciones.json'), JSON.stringify(results,null,2));
        assert.deepEqual(results.filter(r=>r.overflow>1).map(r=>[r.role,r.width,r.overflow]),[]);
        console.log('Validaciones de tamaño y tema:',results.length);
    } finally { await browser.close(); }
})().catch(error=>{console.error(error); process.exitCode=1;});
