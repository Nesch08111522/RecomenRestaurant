from io import BytesIO
from uuid import uuid4

from app import create_app
from database.repository import PostgresDocumentRepository as Repo
from models.market import records
from models.restaurant import RestaurantModel
from models.user import UserModel
from test_business_flow import token


def test_private_inbox_and_claims(test_database, monkeypatch):
    app = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex})
    users, clients = [], []
    for role in ("user", "business_owner", "admin", "user"):
        user = UserModel.create({"username": uuid4().hex, "role": role})
        client = app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = user["id"]
        users.append(user["id"])
        clients.append(client)
    buyer, seller, admin, stranger = clients
    shop = RestaurantModel.create({"owner_id": users[1], "name": "Cocina de prueba", "verified": True})
    rid = shop["id"]
    payload = {"destination": "negocio", "rid": rid, "subject": "Consulta de pedido", "body": "¿Se puede recoger?"}
    assert buyer.post("/bandeja/nueva", data=payload).status_code == 400
    payload["document"] = (BytesIO(b"%PDF-1.4 demo"), "comprobante.pdf")
    response = buyer.post("/bandeja/nueva", data=payload, headers={"X-CSRFToken":token(buyer)})
    assert response.status_code == 302
    path = response.location
    tid = int(path.rsplit("/",1)[1])
    assert buyer.get(path).status_code == 200
    assert seller.get("/bandeja/").status_code == 200
    assert b"Sin leer" in seller.get("/bandeja/?q=Consulta").data
    assert admin.get(path).status_code == stranger.get(path).status_code == 404
    mid = records("thread_messages",tid=tid)[0]["id"]
    assert seller.get(f"{path}/archivo/{mid}").data.startswith(b"%PDF")
    assert stranger.get(f"{path}/archivo/{mid}").status_code == 404
    assert seller.post(path+"/leer",data={"last_id":mid},headers={"X-CSRFToken":token(seller)}).status_code==302
    assert b"Sin leer" not in seller.get("/bandeja/?q=Consulta").data
    assert seller.post(path+"/responder",data={"body":"Sí, hasta las dos."},headers={"X-CSRFToken":token(seller)}).status_code==302
    assert b"Sin leer" in buyer.get("/bandeja/?q=Consulta").data
    for client in (buyer, seller):
        support = client.post("/bandeja/nueva", data={"destination":"soporte","body":"Necesito ayuda","subject":"Pago"},
                              headers={"X-CSRFToken":token(client)})
        assert support.status_code == 302 and admin.get(support.location).status_code == 200
        assert stranger.get(support.location).status_code == 404
    order = Repo.create("market_orders",{"uid":users[0],"rid":rid,"state":"Recibido","lines":[],"business":shop["name"],"total":0,"slot":"2030-01-01T12:00","channel":"Recojo","method":"Contraentrega","history":[]})
    claim = buyer.post(f"/mercado/pedidos/{order['id']}/reclamo",data={"category":"Pago","reason":"Necesito revisar el cobro"},
                       headers={"X-CSRFToken":token(buyer)})
    assert claim.status_code == 302 and b"SR-" in buyer.get(claim.location).data
    assert seller.get(claim.location).status_code == 200 and stranger.get(claim.location).status_code == 404
    update = {"state":"En revisión","priority":"Alta","assigned":users[2],"note":"Verificación de la constancia"}
    assert seller.post(claim.location+"/actualizar",data=update,headers={"X-CSRFToken":token(seller)}).status_code==403
    assert admin.post(claim.location+"/actualizar",data=update,headers={"X-CSRFToken":token(admin)}).status_code==302
    assert b"SR-" in admin.get("/bandeja/reclamos",query_string={"estado":"En revisión","negocio":rid}).data
    assert b"Verificaci" in buyer.get(claim.location).data
    monkeypatch.setattr("utils.ia_qwen.obtener_respuesta_ia", lambda *args,**kwargs: "Revisa la fecha del pago.")
    assert b"Revisa la fecha" in admin.post(claim.location+"/analizar", headers={"X-CSRFToken":token(admin)}).data
    assert stranger.post(claim.location+"/analizar", headers={"X-CSRFToken":token(stranger)}).status_code == 403
    assert buyer.get("/bandeja/notificaciones").status_code == 200
    assert buyer.get("/api/notifications").get_json()["unread_count"] >= 2
