from utils.traceability import build_order_traceability


def test_traceability_uses_immutable_order_snapshot():
    order = {
        "id": 42,
        "rid": 7,
        "business": "Cocina demo",
        "state": "Entregado",
        "created": "2026-11-19T12:00:00+00:00",
        "lines": [
            {
                "offer": 3,
                "dish_id": 8,
                "name": "Ceviche",
                "qty": 2,
                "usage": {
                    "pescado": {
                        "amount": 400,
                        "unit": "g",
                        "lot": "P-001",
                        "expires": "2026-11-20",
                        "recorded_at": "2026-11-19T12:00:00+00:00",
                    }
                },
            }
        ],
    }

    result = build_order_traceability(order)

    assert result["complete"] is True
    assert result["order_id"] == 42
    assert result["lines"][0]["ingredients"][0]["lot"] == "P-001"
    assert result["lines"][0]["ingredients"][0]["expires"] == "2026-11-20"


def test_traceability_marks_legacy_orders_incomplete():
    result = build_order_traceability(
        {"id": 1, "lines": [{"name": "Plato", "usage": {"pescado": {"amount": 100}}}]}
    )

    assert result["complete"] is False
