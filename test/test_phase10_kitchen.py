from datetime import timedelta

from app import create_app
from database.repository import PostgresDocumentRepository as Repo
from logic.market import now
from service_fixtures import login, make_business, make_dish, make_offer, make_store, make_user


def test_kitchen_shows_lot_alerts_and_production_history(service_db):
    owner = make_user("kitchen_owner", "business_owner")
    business = make_business(owner["id"], "Cocina Norteña")
    expired = (now().date() - timedelta(days=1)).isoformat()
    make_store(business["id"], pantry={
        "arroz": {"quantity": 0, "expires": expired, "unit": "g", "cost": 500,
                  "basis": 1000, "substitutes": [], "lot": "lot-arroz"},
        "pollo": {"quantity": 300, "expires": (now().date() + timedelta(days=2)).isoformat(),
                  "unit": "g", "cost": 900, "basis": 1000, "substitutes": ["pavo"], "lot": "lot-pollo"},
    })
    dish = make_dish(business["id"])
    make_offer(business["id"], dish, stock=5)

    app = create_app({"TESTING": True, "SECRET_KEY": "x" * 32, "WTF_CSRF_ENABLED": False})
    client = app.test_client()
    login(client, owner)
    page = client.get(f"/mercado/cocina/{business['id']}")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Alertas de inventario" in body
    assert "Agotado" in body and "Vence pronto" in body
    assert "Historial de producción" in body


def test_service_metrics_use_registered_sessions(service_db):
    from analytics.intelligence import service_metrics
    from models.salon import save_table

    owner = make_user("metrics_owner", "business_owner")
    business = make_business(owner["id"], "Métricas")
    make_store(business["id"])
    table = save_table(business["id"], owner["id"], {"label": "M1", "capacity": 4})
    closed = now()
    opened = closed - timedelta(minutes=55)
    Repo.create("table_sessions", {
        "rid": business["id"], "table_id": table["id"], "token": "c" * 32,
        "uid": owner["id"], "party_size": 2, "status": "Finalizada",
        "opened_at": opened.isoformat(), "closed_at": closed.isoformat(),
        "paid": True, "cleaned_at": closed.isoformat(), "order_ids": [],
    })
    Repo.create("flow_queue", {
        "rid": business["id"], "code": "T-001", "name": "Ana", "party_size": 2,
        "status": "Sentado", "created_at": (closed - timedelta(minutes=20)).isoformat(),
        "called_at": (closed - timedelta(minutes=15)).isoformat(),
        "seated_at": (closed - timedelta(minutes=12)).isoformat(),
        "day": closed.date().isoformat(),
    })
    sessions = [row for row in Repo.all("table_sessions") if row["rid"] == business["id"]]
    queue = [row for row in Repo.all("flow_queue") if row["rid"] == business["id"]]
    result = service_metrics(sessions, queue, 1, closed.date(), closed.date())
    assert result["sessions"] == 1
    assert result["median_minutes"] == 55.0
    assert result["wait_samples"] == 1 and result["median_wait_minutes"] == 8.0
    assert result["rotation_per_table_day"] == 1.0