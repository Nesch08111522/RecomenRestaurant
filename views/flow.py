"""SmartResto Flow: entrada pública, turnos y panel de aforo (fase 11)."""
from __future__ import annotations

from datetime import datetime

from flask import (Blueprint, Response, abort, flash, jsonify, redirect, render_template,
                   request, session as browser, url_for)

from models.flow import (call_next, cancel, demand_pattern, entry, join, no_show, queue,
                         save_settings, seat, settings, status)
from models.restaurant import RestaurantModel
from models.salon import ServiceError, active, all_sessions, snapshot, tables
from utils.catalog_qr import build_queue_qr
from views.salon import is_staff, require_staff, user

flow_bp = Blueprint("flow", __name__)


def _restaurant(rid):
    row = RestaurantModel.get_by_id(rid)
    if not row or not row.get("verified") or row.get("status") in {"suspended", "archived"}:
        abort(404)
    return row


def _remember(rid, qid):
    values = dict(browser.get("queue_ids") or {})
    current = list(values.get(str(rid)) or [])
    if qid not in current:
        current.append(qid)
    values[str(rid)] = current[-10:]
    browser["queue_ids"] = values


def _mine(rid):
    return list((browser.get("queue_ids") or {}).get(str(rid)) or [])


@flow_bp.get("/cola/<int:rid>")
def public(rid):
    restaurant = _restaurant(rid)
    config = settings(rid)
    mine = status(rid, _mine(rid))
    seats = snapshot(rid, mine["waiting"])
    return render_template("flow/public.html", restaurant=restaurant, settings=config,
                           mine=mine, seats=seats, has_tables=bool(tables(rid)),
                           is_staff=is_staff(rid))


@flow_bp.post("/cola/<int:rid>")
def take_turn(rid):
    _restaurant(rid)
    row = join(rid, request.form.get("name", ""), request.form.get("party_size", 1),
               user().get("id"), request.form.get("note", ""))
    _remember(rid, row["id"])
    flash(f"Tu turno es {row['code']}. Puedes seguir tu posición en esta página.", "success")
    return redirect(url_for("flow.public", rid=rid))


@flow_bp.post("/cola/<int:rid>/turno/<int:qid>/cancelar")
def cancel_turn(rid, qid):
    if qid not in _mine(rid):
        abort(403)
    cancel(rid, qid)
    flash("Turno cancelado.", "success")
    return redirect(url_for("flow.public", rid=rid))


@flow_bp.get("/cola/<int:rid>/estado.json")
def public_status(rid):
    _restaurant(rid)
    return jsonify(success=True, **status(rid, _mine(rid)),
                   updated=datetime.now().isoformat(timespec="seconds"))


@flow_bp.get("/salon/<int:rid>/cola")
def desk(rid):
    require_staff(rid)
    restaurant = RestaurantModel.get_by_id(rid) or abort(404)
    config = settings(rid)
    current = queue(rid)
    return render_template("flow/desk.html", restaurant=restaurant, settings=config,
                           queue=current, history=list(reversed(entry_history(rid)))[:30],
                           tables=tables(rid), seats=snapshot(rid, len(current)),
                           pattern=demand_pattern(rid), estimates={
                               row["id"]: estimate_row(rid, row) for row in current})


def entry_history(rid):
    from models.flow import history
    return history(rid)


def estimate_row(rid, row):
    from models.flow import estimate
    return estimate(rid, row["party_size"], position=queue(rid).index(row) + 1)


@flow_bp.post("/salon/<int:rid>/cola/configurar")
def configure(rid):
    require_staff(rid)
    save_settings(rid, accepting=request.form.get("accepting") == "on",
                  max_capacity=request.form.get("max_capacity", 0),
                  note=request.form.get("note", ""))
    flash("Configuración de aforo y cola guardada.", "success")
    return redirect(url_for("flow.desk", rid=rid))


@flow_bp.post("/salon/<int:rid>/cola/<int:qid>/llamar")
def call(rid, qid):
    require_staff(rid)
    call_next(rid, qid)
    flash("Turno llamado.", "success")
    return redirect(url_for("flow.desk", rid=rid))


@flow_bp.post("/salon/<int:rid>/cola/<int:qid>/sentar")
def sit(rid, qid):
    require_staff(rid)
    session = seat(rid, qid, request.form.get("table_id", type=int))
    flash(f"Grupo sentado en la mesa {session.get('table_label') or session.get('table_id')}.", "success")
    return redirect(url_for("flow.desk", rid=rid))


@flow_bp.post("/salon/<int:rid>/cola/<int:qid>/cancelar")
def cancel_staff(rid, qid):
    require_staff(rid)
    cancel(rid, qid)
    flash("Turno cancelado.", "success")
    return redirect(url_for("flow.desk", rid=rid))


@flow_bp.post("/salon/<int:rid>/cola/<int:qid>/ausente")
def absent(rid, qid):
    require_staff(rid)
    no_show(rid, qid)
    flash("Turno marcado como no presentado.", "success")
    return redirect(url_for("flow.desk", rid=rid))


@flow_bp.get("/salon/<int:rid>/cola/qr.svg")
def entry_qr(rid):
    require_staff(rid)
    try:
        content, url = build_queue_qr(rid)
    except ValueError as error:
        raise ServiceError(str(error)) from None
    return Response(content, mimetype="image/svg+xml", headers={
        "Content-Disposition": f'attachment; filename="cola-{rid}.svg"', "Cache-Control": "no-store"})


@flow_bp.get("/salon/<int:rid>/aforo.json")
def occupancy(rid):
    require_staff(rid)
    current = queue(rid)
    return jsonify(success=True, **snapshot(rid, len(current)),
                   updated=datetime.now().isoformat(timespec="seconds"))