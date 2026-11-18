from datetime import date, timedelta

from logic.market import available, weekly_plan, quote, forecast, compatible


def test_shared_ingredients_and_expiry():
    today = date.today().isoformat()
    offer = {"stock": 12, "recipe": {"pollo": 150}, "day": today}
    pantry = {"pollo": {"quantity": 800, "expires": today}}
    assert available(offer, pantry, today) == 5
    assert available(offer, pantry, (date.today() + timedelta(days=1)).isoformat()) == 0


def test_margin_break_even_and_unknown_allergens():
    assert quote(1200, 800, 2000)["break_even"] == 5
    assert quote(700, 800, 2000)["break_even"] is None
    assert not compatible({"allergens": [], "cross": "unknown"}, ["leche"])
    assert not compatible({"allergens": ["leche"], "cross": "declared"}, ["leche"])


def test_weekly_plan_respects_stock_and_total():
    today = date.today()
    rows = [{"id": 7, "name": "Menú", "price": 1200, "available": 2, "day": today.isoformat()}]
    planned = weekly_plan(rows, 2000, today)
    assert sum(item["price"] for item in planned) <= 2000
    assert len(planned) == 1
    assert forecast([], 7, today) is None


def test_weekly_plan_favours_two_affordable_days_over_one_expensive_day():
    today = date.today()
    rows = [{"id": i+1, "name": f"Menú {i}", "price": price, "available": 1,
             "day": (today+timedelta(days=i)).isoformat()} for i, price in enumerate([2000, 900, 1000])]
    assert [r["id"] for r in weekly_plan(rows, 2000, today)] == [2, 3]


def test_market_offer_saves_only_declared_seasons(monkeypatch):
    from contextlib import nullcontext
    from datetime import datetime

    from flask import session
    import pytest

    from app import create_app
    from logic.market import LIMA, MarketError
    from views import market_kitchen

    at = datetime(2026, 11, 18, 12, tzinfo=LIMA)
    saved = []
    monkeypatch.setattr(market_kitchen, 'now', lambda: at)
    monkeypatch.setattr(market_kitchen, 'document_transaction', nullcontext)
    monkeypatch.setattr(market_kitchen, 'lock_business', lambda rid: None)
    monkeypatch.setattr(market_kitchen, 'authorize', lambda rid: {'id': rid})
    monkeypatch.setattr(market_kitchen, 'kitchen', lambda rid: {'channels': ['Delivery'], 'pantry': {}})
    monkeypatch.setattr(market_kitchen, 'commerce_settings', lambda: {'diets': []})
    monkeypatch.setattr(market_kitchen.DishModel, 'get_by_id', staticmethod(
        lambda did: {'id': did, 'name': 'Sopa de quinua', 'restaurant_id': 7}))
    monkeypatch.setattr(market_kitchen.Repo, 'create', staticmethod(
        lambda collection, value: saved.append((collection, value))))

    app = create_app({'TESTING': True, 'SECRET_KEY': 'market-season-test'})
    fields = {'dish': '1', 'day': at.date().isoformat(), 'end': '19:00', 'price': '20', 'stock': '5',
              'occasion': 'Almuerzo', 'cross': 'unknown', 'variant': 'Porción familiar'}
    with app.test_request_context('/mercado/cocina/7/oferta', method='POST',
                                  data={**fields, 'seasons': ['Invierno', 'Otoño']}):
        session['user_id'] = 1
        assert market_kitchen.publish(7).status_code == 302
    collection, offer = saved[0]
    assert collection == 'market_offers' and offer['seasons'] == ['Otoño', 'Invierno']
    assert offer['variant'] == 'Porción familiar' and offer['review_state'] == 'pending'

    with app.test_request_context('/mercado/cocina/7/oferta', method='POST',
                                  data={**fields, 'seasons': ['Carnaval']}):
        with pytest.raises(MarketError, match='temporadas'):
            market_kitchen.publish(7)
    assert len(saved) == 1
