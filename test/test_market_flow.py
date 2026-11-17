from datetime import timedelta
import io
from PIL import Image
from uuid import uuid4

from app import create_app
from logic.market import now
from models.market import kitchen, records
from models.restaurant import RestaurantModel
from models.user import UserModel


def test_market_sale_reaches_inventory_reputation_and_repeat_purchase(test_database, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    app = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex, "WTF_CSRF_ENABLED": False})
    owner, buyer, stranger, admin = [app.test_client() for _ in range(4)]
    ids = []
    for client, role in [(owner, "business_owner"), (buyer, "user"), (stranger, "business_owner"), (admin, "admin")]:
        user = UserModel.create({"username": uuid4().hex, "role": role})
        ids.append(user["id"])
        with client.session_transaction() as session:
            session["user_id"] = user["id"]
    shop = RestaurantModel.create({"name": "Cocina " + uuid4().hex[:8], "owner_id": ids[0], "district": "Moche", "verified": True})
    rid = shop["id"]
    desk = f"/mercado/cocina/{rid}"
    assert stranger.get(desk).status_code == 403
    assert owner.get(desk).status_code == 200
    assert owner.post(desk + "/configurar", data={"channels":"Recojo","kind":"Comida casera","pickup":"Plaza",
                                                   "loyalty":"10","capacity":"3"}).status_code == 302
    tomorrow = (now().date() + timedelta(days=1)).isoformat()
    assert owner.post(desk + "/inventario", data={"move":"Entrada","name":"Arroz","quantity":1000,"unit":"g",
        "expires":tomorrow,"cost":"5","basis":1000}).status_code == 302
    image = io.BytesIO()
    Image.new("RGB", (400, 350), "orange").save(image, "JPEG")
    image.seek(0)
    assert owner.post(desk + "/foto", data={"photo":(image,"arroz.jpg")}).status_code == 200
    assert owner.post(desk + "/oferta", data={"name":"Arroz norteño","day":tomorrow,"end":"20:00", "use_photo":"1",
        "price":"15","stock":8,"recipe":"arroz=200","occasion":"Almuerzo","cross":"declared","declared":"on"}).status_code == 302
    listing = records("market_offers", rid=rid)[0]
    oid = listing["id"]
    assert buyer.get(f"/mercado/oferta/{oid}/foto").mimetype == "image/jpeg"
    assert owner.post(desk+"/simular", data={"recipe":"arroz=200","price":15,"fixed":30}).status_code == 200
    assert stranger.post(desk+"/inventario", data={"name":"Arroz","quantity":2,"move":"Merma"}).status_code == 403
    assert buyer.get("/mercado/", query_string={"day":tomorrow,"budget":16,"avoid":"leche"}).status_code == 200
    assert buyer.post("/mercado/carrito", data={"offer":oid,"qty":2}).status_code == 302
    assert buyer.get("/mercado/carrito").status_code == 200
    payload = {"slot":tomorrow+"T13:00","channel":"Recojo","method":"Contraentrega","total":3000}
    assert buyer.post("/mercado/comprar", data=payload).status_code == 302
    assert kitchen(rid)["pantry"]["arroz"]["quantity"] == 600
    order = records("market_orders", rid=rid)[0]
    for state in ["Preparando","Listo","Entregado"]:
        assert owner.post(desk + f"/pedido/{order['id']}", data={"action":state}).status_code == 302
    assert buyer.post(f"/mercado/pedidos/{order['id']}/valorar", data={"rating":5,"comment":"Muy bueno"}).status_code == 302
    assert records("reviews", order_id=order["id"])[0]["verified_purchase"]
    assert buyer.post(f"/mercado/pedidos/{order['id']}/reclamo", data={"reason":"Quisiera revisar el horario acordado",
                      "document":(io.BytesIO(b"%PDF-1.4\n%test"),"evidencia.pdf")}).status_code == 302
    case = records("market_cases", oid=order["id"])[0]
    assert admin.get("/mercado/confianza").status_code == 200
    download = f"/mercado/confianza/{case['id']}/documento"
    assert admin.get(download).data.startswith(b"%PDF")
    assert stranger.get(download).status_code == 403
    assert admin.post(f"/mercado/confianza/{case['id']}", data={"result":"Aceptado","note":"Revisión completada"}).status_code == 302
    assert buyer.get("/mercado/pedidos").status_code == 200
    assert buyer.post(f"/mercado/pedidos/{order['id']}/repetir").status_code == 302
    assert buyer.post("/mercado/carrito/vaciar").status_code == 302
    assert buyer.post("/mercado/carrito", data={"offer":oid,"qty":1}).status_code == 302
    assert b"13.50" in buyer.get("/mercado/carrito").data
    assert buyer.post("/mercado/comprar", data={**payload,"total":1350}).status_code == 302
    second = records("market_orders",rid=rid)[-1]
    assert buyer.post(f"/mercado/pedidos/{second['id']}/cancelar").status_code == 302
    assert kitchen(rid)["pantry"]["arroz"]["quantity"] == 600
    assert buyer.post(f"/mercado/pagos/{rid}/notificar?data.id=1").status_code == 403
    UserModel.update(ids[0], {"role":"user"})
    assert owner.get(desk).status_code == 403

