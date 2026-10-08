from analytics.metrics import build_bi_snapshot


def test_bi_snapshot_is_real_data_only_and_versioned():
    snapshot = build_bi_snapshot(
        users=[{"id": 1, "role": "user"}, {"id": 2, "role": "owner"}],
        restaurants=[{"id": 10, "category_id": 3, "verified": True, "rating": 4.5}],
        dishes=[{"id": 5, "restaurant_id": 10, "is_available": True}],
        menus=[{"id": 1, "restaurant_id": 10}],
        favorites=[{"user_id": 1, "restaurant_id": 10}],
        reviews=[{"user_id": 1, "restaurant_id": 10, "rating": 5}],
        audit_events=[{"action": "ADMIN_APPROVAL_DECISION", "actor_user_id": 2}],
        categories=[{"id": 3, "name": "Italiana"}],
    )
    assert snapshot["export"]["schema_version"] == "bi.v1"
    assert snapshot["users"]["by_role"] == {"user": 1, "owner": 1}
    assert snapshot["business"]["restaurants_by_status"]["APROBADO"] == 1
    assert snapshot["business"]["restaurants_by_category"]["Italiana"] == 1
    assert snapshot["quality"]["average_review_rating"] == 5.0
    assert snapshot["quality"]["recommendation_feedback_status"] == "INSUFICIENTE_PARA_EVALUACION"
    assert "password" not in str(snapshot).lower()


def test_bi_snapshot_does_not_invent_empty_metrics():
    snapshot = build_bi_snapshot()
    assert snapshot["quality"]["average_review_rating"] is None
    assert snapshot["quality"]["average_restaurant_rating"] is None
    assert snapshot["business"]["menus_total"] == 0
