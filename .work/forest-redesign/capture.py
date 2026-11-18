from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.work/forest-redesign/previews'
OUT.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    context=browser.new_context(locale='es-PE', reduced_motion='reduce')
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:5002/',wait_until='domcontentloaded',timeout=60000)
    page.wait_for_timeout(4000)
    for width in [320,375,640,768,1024,1440,1920]:
        page.set_viewport_size({'width':width,'height':1024})
        page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
        page.wait_for_timeout(1200)
        page.evaluate('window.scrollTo(0,0)')
        page.wait_for_timeout(250)
        results.append(page.evaluate('''() => ({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,body:document.body.className,cards:document.querySelectorAll('#resultsGrid .restaurant-card').length,grid:getComputedStyle(document.querySelector('#resultsGrid')).gridTemplateColumns,mainTop:document.querySelector('main').getBoundingClientRect().top,header:document.querySelector('.sr-header').getBoundingClientRect().height,imageHeight:document.querySelector('.card-image').offsetHeight,cardHeight:document.querySelector('.restaurant-card').offsetHeight,mapVisible:!document.querySelector('.map-column').hidden,brokenImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.getAttribute('src'))})'''))
        if width in [375,768,1440]:
            page.screenshot(path=str(OUT/f'home-{width}.png'),full_page=True)
            page.screenshot(path=str(OUT/f'viewport-{width}.png'))
    page.locator('#themeToggle').click()
    page.screenshot(path=str(OUT/'dark-1440.png'),full_page=True)
    results.append({'pageErrors':errors})
    context.close();browser.close()
(OUT/'measurements.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=True,indent=2))
