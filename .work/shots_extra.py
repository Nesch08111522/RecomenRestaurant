# -*- coding: utf-8 -*-
import json, urllib.request, os
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = r"C:\Users\Nancy Sandoval\Downloads\SISRESTAURANTE\RecomenRestaurant\.work\screenshots"

def get(u):
    r = urllib.request.urlopen(BASE + u, timeout=15)
    return json.loads(r.read().decode("utf-8"))

top = get("/api/restaurants/top-rated")
rids = [r.get("id") for r in top.get("results", [])][:3]
print("restaurant ids:", rids)

extra = [("/recomendaciones", "recomendaciones"), ("/ciudad", "ciudad")]
if rids:
    extra.insert(0, (f"/restaurant/{rids[0]}", "restaurante_detalle"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    for path, name in extra:
        try:
            page.goto(BASE + path, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2500)
            page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=True)
            print(f"OK {name} -> {page.title()!r}")
        except Exception as e:
            print(f"FAIL {name}: {e!r}")
    browser.close()
print("done")
