from pathlib import Path
import json
from playwright.sync_api import sync_playwright
OUT=Path(__file__).resolve().parent/'previews'
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True)
    page=b.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:5002/',wait_until='domcontentloaded',timeout=60000)
    page.wait_for_timeout(4000)
    count=page.locator('#resultsGrid .restaurant-card').count()
    page.locator('#forest-map').click()
    page.wait_for_timeout(7000)
    result=page.evaluate('''() => ({mapVisible:!document.querySelector('.map-column').hidden,mapLibreReady:!!window.mapGL,leafletReady:!!document.querySelector('.leaflet-pane'),mapCanvas:!!document.querySelector('.maplibregl-canvas'),cards:document.querySelectorAll('#resultsGrid .restaurant-card').length,tilesLoaded:window.mapGL?.map.isStyleLoaded() || false})''')
    assert result['mapVisible']
    assert result['mapLibreReady'] or result['leafletReady']
    assert result['cards']==count
    page.locator('#forest-list').click()
    assert not page.locator('.map-column').is_visible()
    result['pageErrors']=errors
    (OUT/'map-smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    b.close()
