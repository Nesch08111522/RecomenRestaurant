
from app import create_app

app = create_app({"TESTING": True})

print("ENDPOINT:", app.view_functions["ai.interpret"])
print(
    "VISTAS EXENTAS:",
    sorted(app.extensions["csrf"]._exempt_views)
)

client = app.test_client()

response = client.post(
    "/api/ai/interpret",
    json={
        "text": "Busco comida criolla económica",
        "categories": [{"id": 1, "name": "Criolla"}],
        "available_tags": ["criolla", "económico"]
    }
)

print("\nESTADO HTTP:", response.status_code)
print("RESPUESTA:", response.get_json(silent=True))
