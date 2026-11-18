import sys, json, importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('home_test',ROOT/'test/test_forest_home.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from playwright.sync_api import sync_playwright
server=m.visual_origin.__wrapped__();origin=next(server)
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':320,'height':900})
 page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(origin) else r.abort())
 page.goto(origin+'/__forest_test');page.wait_for_load_state('networkidle')
 print(json.dumps(page.evaluate('''() => ['body','.forest-hero h1','.forest-section-heading h2','.restaurant-card','.card-content','.card-content h3','.card-location','.rating','.card-price','.forest-card-bottom','.card-tags','.tag','.card-link'].map(s=>{const el=document.querySelector(s),c=getComputedStyle(el);return {s,font:c.fontSize,family:c.fontFamily,line:c.lineHeight,height:el.getBoundingClientRect().height,margin:c.margin,padding:c.padding};})'''),indent=2))
 page.screenshot(path=str(ROOT/'.work/forest-redesign/previews/diagnose-320.png'),full_page=True)
 b.close()
server.close()
