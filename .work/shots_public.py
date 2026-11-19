# -*- coding: utf-8 -*-
import os
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = r"C:\Users\Nancy Sandoval\Downloads\SISRESTAURANTE\RecomenRestaurant\.work\screenshots"
os.makedirs(OUT, exist_ok=True)

pages = [
    ("/", "home"),
    ("/mercado", "mercado"),
    ("/auth/login", "login"),
    ("/auth/register", "register"),
    ("/explorar", "explorar"),
    ("/ofertas", "ofertas"),
    ("/para-negocios", "para_negocios"),
]


def snap(page, path, name, tag=""):
    page.goto(BASE + path, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(2500)
    page.screenshot(path=os.path.join(OUT, f"{name}{tag}.png"), full_page=True)
    print(f"OK {name}{tag} -> {page.title()!r}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    for path, name in pages:
        try:
            snap(page, path, name)
        except Exception as e:
            print(f"FAIL {name}: {e!r}")
    # captura responsive (móvil) de la portada y el mercado
    try:
        mob = browser.new_page(viewport={"width": 390, "height": 844})
        for path, name in [("/", "home"), ("/mercado", "mercado")]:
            try:
                snap(mob, path, name, tag="_movil")
            except Exception as e:
                print(f"FAIL {name}_movil: {e!r}")
        mob.close()
    except Exception as e:
        print(f"FAIL movil: {e!r}")
    browser.close()
print("done")
