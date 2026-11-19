from uuid import uuid4

from app import create_app
from models.market import records
from models.salon import save_table
from service_fixtures import (login, make_business, make_dish, make_offer, make_store,
                              make_user)


def app_client():
    return flask_app().test_client()


def flask_app():
    return create_app({"TESTING": True, "SECRET_KEY": "x" * 32, "WTF_CSRF_ENABLED": False})


def setup(service_db):
    owner = make_user("route_owner", "business_owner", "Dueño Ruta")
    diner = make_user("route_diner", "user", "Comensal Ruta")
    business = make_business(owner["id"], "Ruta Norteño")
    make_store(business["id"])
    dish = make_dish(business["id"])
    offer = make_offer(business["id"], dish, stock=5)
    table = save_table(business["id"], owner["id"], {"label": "08", "floor": "Segundo piso",
                                                     "zone": "Terraza", "capacity": 4})
    return owner, diner, business, dish, offer, table


def test_public_qr_menu_does_not_open_or_expose_identity(service_db):
    owner, diner, business, dish, offer, table = setup(service_db)
    client = app_client()
    response = client.get(f"/mesa/{table['qr_token']}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Ruta Norteño" in body and "Mesa 08" in body and "Disponible" in body
    assert "route_diner" not in body
    assert not records("table_sessions", table_id=table["id"])


def test_guest_cannot_open_a_table(service_db):
    owner, diner, business, dish, offer, table = setup(service_db)
    client = app_client()
    response = client.post(f"/mesa/{table['qr_token']}/abrir", data={"people": 2})
    assert response.status_code == 401
    assert not records("table_sessions", table_id=table["id"])


def test_table_flow_orders_requests_and_split(service_db):
    owner, diner, business, dish, offer, table = setup(service_db)
    app = flask_app()
    client = app.test_client()
    login(client, diner)

    opened = client.post(f"/mesa/{table['qr_token']}/abrir", data={"people": 2})
    assert opened.status_code == 302
    session = records("table_sessions", table_id=table["id"])[0]
    assert session["uid"] == diner["id"]

    added = client.post(f"/mesa/{table['qr_token']}/carrito", data={"offer": offer["id"], "qty": 1})
    assert added.status_code == 302
    cart_page = client.get(f"/mesa/{table['qr_token']}/carrito")
    assert "Arroz con pollo" in cart_page.get_data(as_text=True)

    placed = client.post(f"/mesa/{table['qr_token']}/pedido", data={"total": 1800})
    assert placed.status_code == 302
    rows = records("market_orders", table_session=session["id"])
    assert len(rows) == 1 and rows[0]["channel"] == "Local" and rows[0]["table_label"] == "08"

    assert client.post(f"/mesa/{table['qr_token']}/solicitar", data={"kind": "Mozo"}).status_code == 302
    assert records("service_requests", session_id=session["id"])[0]["kind"] == "Mozo"

    divided = client.post(f"/mesa/{table['qr_token']}/dividir", data={"people": 2})
    assert divided.status_code == 302
    saved = records("table_sessions", table_id=table["id"])[0]
    assert [row["amount"] for row in saved["split"]["shares"]] == [900, 900]

    page = client.get(f"/mesa/{table['qr_token']}/sesion")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Pedido #" in body and "Solicitudes pendientes" in body and "División del consumo" in body

    status = client.get(f"/mesa/{table['qr_token']}/estado.json").get_json()
    assert status["session"]["total"] == 1800


def test_staff_desk_and_queue_are_scoped_to_the_business(service_db):
    owner, diner, business, dish, offer, table = setup(service_db)
    app = flask_app()
    staff_client = app.test_client()
    login(staff_client, owner)
    assert staff_client.get(f"/owner/salon/{business['id']}").status_code == 200
    assert staff_client.get(f"/salon/{business['id']}").status_code == 200
    assert staff_client.get(f"/salon/{business['id']}/cola").status_code == 200
    assert staff_client.get(f"/owner/puntos/{business['id']}").status_code == 200
    assert staff_client.get(f"/owner/salon/{business['id']}/mesa/{table['id']}/qr.svg").status_code == 200

    diner_client = app.test_client()
    login(diner_client, diner)
    assert diner_client.get(f"/salon/{business['id']}").status_code == 403
    assert diner_client.get(f"/owner/salon/{business['id']}").status_code == 404
    assert diner_client.get("/puntos").status_code == 200

    other = make_user("other_owner", "business_owner")
    other_client = app.test_client()
    login(other_client, other)
    assert other_client.get(f"/owner/salon/{business['id']}").status_code == 404


def test_public_queue_registration_and_staff_seating(service_db):
    owner, diner, business, dish, offer, table = setup(service_db)
    app = flask_app()
    guest = app.test_client()
    page = guest.get(f"/cola/{business['id']}")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Cola virtual" in body and "Aforo por piso" in body

    joined = guest.post(f"/cola/{business['id']}", data={"name": "Ana", "party_size": 2})
    assert joined.status_code == 302
    state = guest.get(f"/cola/{business['id']}/estado.json").get_json()
    assert state["mine"][0]["code"] == "T-001"
    assert all("name" not in row for row in state["ahead"])

    staff = app.test_client()
    login(staff, owner)
    qid = state["mine"][0]["id"]
    assert staff.post(f"/salon/{business['id']}/cola/{qid}/llamar").status_code == 302
    seated = staff.post(f"/salon/{business['id']}/cola/{qid}/sentar", data={"table_id": table["id"]})
    assert seated.status_code == 302
    assert records("table_sessions", table_id=table["id"])[0]["party_size"] == 2


def test_flow_settings_and_occupancy_json(service_db):
    owner, diner, business, dish, offer, table = setup(service_db)
    client = app_client()
    login(client, owner)
    saved = client.post(f"/salon/{business['id']}/cola/configurar",
                        data={"accepting": "on", "max_capacity": 12, "note": "Terraza"})
    assert saved.status_code == 302
    data = client.get(f"/salon/{business['id']}/aforo.json").get_json()
    assert data["seats"] == 4 and data["available_tables"] == 1