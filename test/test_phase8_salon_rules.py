import pytest

from logic.salon import (ServiceError, occupancy_snapshot, public_session, split_equal,
                         table_state, validate_shares, wait_estimate)


def test_table_state_uses_pending_requests_before_cooking_state():
    session = {"id": 1, "status": "Abierta", "party_size": 2}
    orders = [{"state": "Preparando", "total": 1800}]
    assert table_state(session, orders) == "En preparación"
    assert table_state(session, orders, [{"kind": "Mozo", "status": "Pendiente"}]) == "Solicita atención"
    assert table_state(session, orders, [{"kind": "Cuenta", "status": "Pendiente"}]) == "Solicita cuenta"
    assert table_state({**session, "status": "Pago"}, orders) == "Pendiente de pago"


def test_scan_alone_never_occupies_a_table():
    assert table_state(None, [], []) == "Disponible"


def test_finished_session_stays_in_cleaning_until_released():
    session = {"id": 1, "status": "Finalizada", "cleaned_at": None}
    assert table_state(session, [], [], cleaned=False) == "Limpieza"
    assert table_state(session, [], [], cleaned=True) == "Disponible"


def test_equal_split_never_loses_a_cent():
    shares = split_equal(1001, 3)
    assert shares == [334, 334, 333]
    assert sum(shares) == 1001
    assert split_equal(0, 2) == [0, 0]


def test_split_rejects_invalid_ranges_and_mismatched_custom_shares():
    with pytest.raises(ServiceError):
        split_equal(1000, 1)
    with pytest.raises(ServiceError):
        split_equal(1000, 31)
    assert validate_shares([500, 500], 1000) == [500, 500]
    with pytest.raises(ServiceError):
        validate_shares([400, 500], 1000)


def test_wait_estimate_is_zero_when_a_suitable_table_is_free():
    result = wait_estimate([], 1, 1, 0, 45)
    assert result["minutes"] == 0 and result["basis"] == "mesa disponible ahora"


def test_wait_estimate_declares_insufficient_history():
    result = wait_estimate([], 0, 2, 0, 45)
    assert result["minutes"] == 45
    assert "declarada" in result["basis"] and result["samples"] == 0


def test_wait_estimate_uses_real_sessions_when_available():
    result = wait_estimate([40, 50, 60, 70], 0, 1, 1, 90)
    assert result["samples"] == 4
    assert result["low"] < result["minutes"] < result["high"]
    assert "historial" in result["basis"]


def test_wait_estimate_without_tables_for_that_party_size():
    assert wait_estimate([], 0, 0, 0, 45)["minutes"] is None


def test_occupancy_snapshot_counts_only_active_sessions():
    tables = [
        {"id": 1, "capacity": 4, "floor": "Piso 1", "zone": "Salón"},
        {"id": 2, "capacity": 2, "floor": "Piso 1", "zone": "Terraza"},
    ]
    sessions = [{"table_id": 1, "party_size": 3, "status": "Abierta"},
                {"table_id": 2, "party_size": 2, "status": "Finalizada"}]
    result = occupancy_snapshot(tables, sessions, waiting=2)
    assert result["seats"] == 6 and result["occupied"] == 3
    assert result["available_tables"] == 1 and result["waiting"] == 2
    assert result["occupancy"] == 50.0


def test_public_session_does_not_expose_guest_identity():
    session = {"id": 9, "status": "Abierta", "party_size": 2, "uid": 5, "guest_name": "Ana"}
    view = public_session(session, [{"id": 1, "state": "Recibido", "total": 1800,
                                     "lines": [{"name": "Arroz", "qty": 1, "unit": 1800}]}])
    assert view["total"] == 1800
    assert "uid" not in view and "guest_name" not in view
    assert view["orders"][0]["lines"] == [{"name": "Arroz", "qty": 1}]