# -*- coding: utf-8 -*-
import json, urllib.request, os

OUT = r"C:\Users\Nancy Sandoval\Downloads\SISRESTAURANTE\RecomenRestaurant\.work\screenshots"

def get(u):
    try:
        r = urllib.request.urlopen("http://127.0.0.1:5000" + u, timeout=15)
        return r.status, json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return "ERR", repr(e)[:100]

for n in ["home", "mercado", "login", "register", "explorar", "ofertas", "para_negocios", "home_movil", "mercado_movil"]:
    p = os.path.join(OUT, n + ".png")
    print(n, os.path.getsize(p) if os.path.exists(p) else "MISSING", "bytes")

print("--- API ---")
for u in ["/api/categories", "/api/restaurants/top-rated", "/api/restaurants/nearby?lat=-8.1118&lng=-79.0287", "/api/search"]:
    s, d = get(u)
    if isinstance(d, dict):
        keys = list(d.keys())[:8]
        print(u, s, "dict keys:", keys, "count:", d.get("count"), "total:", d.get("total"))
    elif isinstance(d, list):
        print(u, s, "list len:", len(d))
    else:
        print(u, s, d)
