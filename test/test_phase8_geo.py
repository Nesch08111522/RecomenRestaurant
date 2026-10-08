from logic.hybrid_recommender import recommend
from utils.geo import calculate_distance, normalize_coordinates


def test_coordinates_are_normalized_and_finite():
    assert normalize_coordinates("0", "0") == (0.0, 0.0)
    assert normalize_coordinates("91", "0") is None
    assert normalize_coordinates("nan", "0") is None


def test_distance_is_deterministic_and_invalid_data_is_not_nearby():
    assert calculate_distance(0, 0, 0, 0) == 0.0
    assert calculate_distance(None, 0, 0, 0) == 999.99


def test_recommendation_does_not_claim_open_status_without_explicit_signal():
    result = recommend([{"id": 1, "rating": 4, "distance_km": 2}], {"id": 1}, {})[0]
    assert "is_open_now" not in result
    assert all("horario" not in reason.lower() for reason in result["recommendation"]["reasons"])
