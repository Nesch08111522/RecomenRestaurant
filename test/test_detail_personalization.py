from flask import Flask, g
from logic.hybrid_recommender import explain_detail


def test_restrictions_require_all_evidence():
    result = explain_detail({'dietary_restrictions': ['vegano']},
                            {'restrictions': ['vegano', 'sin gluten'], 'preferences': []}, [])
    assert result['compatible'] is False
    assert any('sin gluten' in value for value in result['exclusions'])


def test_preferences_and_unknown_allergy():
    result = explain_detail({'tags': ['criolla']},
                            {'preferences': ['criolla'], 'restrictions': ['alergia mani']}, [])
    assert result['reasons'] == ['Coincide con tu preferencia: criolla']
    assert not result['compatible']
    assert result['source'] == 'registered_evidence'


def test_profile_uses_current_account(monkeypatch):
    from views import main
    app = Flask(__name__)
    app.secret_key = 'test-only'
    with app.test_request_context('/'):
        from flask import session
        session['user'] = {'id': 12, 'profile': {'preferences': ['old']}}
        g.account_record = {'id': 12, 'profile': {'preferences': ['new'], 'restrictions': ['vegano']}}
        assert main.get_user_profile()['preferences'] == ['new']


def test_ai_failure_returns_evidence_without_database(monkeypatch):
    from views import main
    import utils.llm_provider as provider
    app = Flask(__name__)
    app.secret_key = 'test-only'
    app.register_blueprint(main.main_bp)
    monkeypatch.setattr(main.RestaurantModel, 'get_by_id', lambda rid: {'id': rid, 'verified': True})
    monkeypatch.setattr(main, 'load_dishes', lambda rid: [])
    monkeypatch.setattr(main, 'get_user_profile', lambda: {'restrictions': ['sin gluten']})
    monkeypatch.setattr(provider, 'settings', lambda: (_ for _ in ()).throw(provider.AIUnavailable()))
    with app.test_client() as client:
        with client.session_transaction() as session:
            session['user'] = {'id': 12}
        response = client.post('/api/restaurant/1/analyze')
    assert response.status_code == 503
    assert response.json['explanation']['compatible'] is False


def test_favorites_read_legacy_string_identity(monkeypatch):
    from models.favorite import FavoriteModel
    monkeypatch.setattr(FavoriteModel, 'all', lambda: [
        {'user_id': '12', 'restaurant_id': 3}, {'user_id': 13, 'restaurant_id': 4}])
    assert FavoriteModel.get_favorite_restaurant_ids(12) == [3]


def test_analyze_requires_login():
    from views import main
    app = Flask(__name__)
    app.secret_key = 'test-only'
    app.register_blueprint(main.main_bp)
    assert app.test_client().post('/api/restaurant/1/analyze').status_code == 401
