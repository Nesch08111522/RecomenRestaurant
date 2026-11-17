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
