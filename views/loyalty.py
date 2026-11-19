"""Billetera de puntos, visitas y reputación del comensal (fase 12)."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models.loyalty import (birthday_claim, owner_customers, save_preferences, visits, wallet)
from models.restaurant import RestaurantModel
from models.review import ReviewModel
from models.user import UserModel
from views.salon import is_staff, require_user, user

loyalty_bp = Blueprint("loyalty", __name__)


@loyalty_bp.get("/puntos")
def wallet_page():
    actor = require_user()
    account = UserModel.get_by_id(actor["id"]) or {}
    profile = account.get("profile") or {}
    return render_template("loyalty/wallet.html", account=account,
                           wallet=wallet(actor["id"]), visits=visits(actor["id"]),
                           preferences=(profile.get("loyalty") or {}),
                           birthday=str(profile.get("birthday") or "")[:10])


@loyalty_bp.post("/puntos/cumpleanos")
def birthday():
    actor = require_user()
    try:
        row = birthday_claim(actor["id"])
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash(f"Beneficio de cumpleaños acreditado: {row['points']} puntos.", "success")
    return redirect(url_for("loyalty.wallet_page"))


@loyalty_bp.post("/puntos/preferencias")
def preferences():
    actor = require_user()
    save_preferences(actor["id"], marketing=request.form.get("marketing") == "on",
                     visits_visible=request.form.get("visits_visible") == "on",
                     birthday_visible=request.form.get("birthday_visible") == "on")
    flash("Preferencias de fidelización guardadas.", "success")
    return redirect(url_for("loyalty.wallet_page"))


@loyalty_bp.get("/owner/puntos/<int:rid>")
def customers(rid):
    actor = user()
    if not actor.get("id"):
        abort(401)
    restaurant = RestaurantModel.get_by_id(rid)
    if not restaurant or not is_staff(rid):
        abort(404)
    return render_template("loyalty/customers.html", restaurant=restaurant,
                           data=owner_customers(rid),
                           rating=ReviewModel.get_rating_stats(rid))