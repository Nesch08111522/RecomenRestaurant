"""Authenticated inbox and formal claim tracking."""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import MarketError, integer, now
from models.communication import (PRIORITIES, STATES, admins, attachment, case_code,
                                  case_event, case_state, download, notify)
from models.market import records
from models.notification import NotificationModel
from models.restaurant import RestaurantModel
from views.market import identity, validation

bp = Blueprint("comunicacion", __name__, url_prefix="/bandeja")
bp.register_error_handler(MarketError, validation)


def can_read(thread, user):
    return (user["id"] in thread["participants"] or
            (thread["support"] and user["role"] == "admin"))


def fetch_thread(tid, lock=False):
    thread = Repo.get_by_id("threads", tid, for_update=lock)
    if not thread or not can_read(thread, identity()):
        abort(404)
    return thread


def pending(thread, uid):
    return thread.get("last_id", 0) > thread.get("seen", {}).get(str(uid), 0)


@bp.get("/pendientes")
def unread_counts():
    user = identity()
    with document_transaction() as conn:
        count = conn.execute("""SELECT count(*) AS n FROM public.app_records WHERE collection='threads'
            AND (payload @> %s OR (%s AND payload @> '{"support":true}'::jsonb))
            AND (payload->>'last_id')::bigint > COALESCE((payload->'seen'->>%s)::bigint,0)""",
            (Repo._jsonb({"participants":[user["id"]]}), user["role"] == "admin", str(user["id"]))).fetchone()["n"]
    return jsonify(mensajes=count, notificaciones=NotificationModel.get_unread_count(user["id"]))


@bp.get("/")
def inbox():
    user = identity()
    rows = records("threads", participants=[user["id"]])
    if user["role"] == "admin":
        rows += records("threads", support=True)
    query = request.args.get("q", "").strip().casefold()
    rows = [t for t in {t["id"]: t for t in rows}.values() if query in
            " ".join([t["subject"], t["business"], str(t.get("oid") or "")]).casefold()]
    return render_template("communication/inbox.html", threads=sorted(rows, key=lambda t:t["updated"], reverse=True),
                           pending=pending, uid=user["id"], businesses=RestaurantModel.get_approved(), q=query)


def post_message(thread, user):
    body = request.form.get("body", "").strip()
    if not 1 <= len(body) <= 3000:
        raise MarketError("Escribe un mensaje de hasta 3000 caracteres.")
    evidence = attachment(request.files.get("document"), thread.get("rid"))
    at = now().isoformat()
    message = Repo.create("thread_messages", {"tid": thread["id"], "author": user["id"],
        "name": user.get("username") or user.get("name") or "Participante", "body": body,
        "created": at, "evidence": evidence})
    seen = dict(thread.get("seen", {}))
    seen[str(user["id"])] = message["id"]
    Repo.update("threads", thread["id"], {"seen": seen, "last_id": message["id"], "updated": at})
    recipients = set(thread["participants"])
    if thread["support"]:
        recipients.update(u["id"] for u in admins())
    notify(recipients - {user["id"]}, "Nuevo mensaje", thread["subject"],
           url_for("comunicacion.thread", tid=thread["id"]))


@bp.post("/nueva")
def start():
    user = identity()
    subject = request.form.get("subject", "").strip()
    if not 1 <= len(subject) <= 120:
        raise MarketError("Indica un asunto de hasta 120 caracteres.")
    destination = request.form.get("destination")
    oid = request.form.get("oid")
    with document_transaction():
        participants = [user["id"]]
        business = {}
        if oid:
            oid = integer(oid, 1)
            order = Repo.get_by_id("market_orders", oid)
            if not order or order["uid"] != user["id"]:
                abort(404)
            business = RestaurantModel.get_by_id(order["rid"]) or {}
        if destination == "negocio":
            if not oid:
                business = RestaurantModel.get_by_id(integer(request.form.get("rid"), 1)) or {}
            if not business or (not oid and not business.get("verified")):
                abort(404)
            if user["id"] == business["owner_id"]:
                raise MarketError("Elige otro negocio para enviar un mensaje.")
            participants.append(business["owner_id"])
        elif destination != "soporte":
            raise MarketError("Selecciona negocio o soporte.")
        thread = Repo.create("threads", {"participants": participants, "support": destination == "soporte",
            "rid": business.get("id"), "business": business.get("name", "Soporte"), "oid": oid,
            "subject": subject, "updated": now().isoformat()})
        post_message(thread, user)
    return redirect(url_for("comunicacion.thread", tid=thread["id"]))


@bp.get("/mensajes/<int:tid>")
def thread(tid):
    thread = fetch_thread(tid)
    user = identity()
    threads = records("threads", participants=[user["id"]])
    if user["role"] == "admin":
        threads += records("threads", support=True)
    threads = sorted({t["id"]: t for t in threads}.values(), key=lambda t: t["updated"], reverse=True)
    return render_template("communication/thread.html", thread=thread, messages=records("thread_messages",tid=tid),
                            threads=threads, uid=user["id"], pending=pending)


@bp.post("/mensajes/<int:tid>/responder")
def reply(tid):
    with document_transaction():
        post_message(fetch_thread(tid, lock=True), identity())
    return redirect(url_for("comunicacion.thread", tid=tid))


@bp.post("/mensajes/<int:tid>/leer")
def seen(tid):
    with document_transaction():
        thread = fetch_thread(tid, lock=True)
        seen_by = dict(thread.get("seen", {}))
        visible = integer(request.form.get("last_id"), 1)
        seen_by[str(identity()["id"])] = max(seen_by.get(str(identity()["id"]), 0),
                                             min(visible, thread["last_id"]))
        Repo.update("threads", tid, {"seen": seen_by})
    return redirect(url_for("comunicacion.thread", tid=tid))


@bp.get("/mensajes/<int:tid>/archivo/<int:mid>")
def file(tid, mid):
    fetch_thread(tid)
    message = Repo.get_by_id("thread_messages", mid)
    if not message or message["tid"] != tid:
        abort(404)
    return download(message.get("evidence"))


def case_access(case, user):
    if not case or case["kind"] != "Reclamo":
        abort(404)
    owner = (RestaurantModel.get_by_id(case["rid"]) or {}).get("owner_id")
    if user["role"] != "admin" and user["id"] not in (owner, case["uid"]):
        abort(404)


@bp.get("/reclamos")
def cases():
    user = identity()
    if user["role"] == "admin":
        rows = records("market_cases", kind="Reclamo")
    else:
        rows = records("market_cases", uid=user["id"], kind="Reclamo")
        for business in RestaurantModel.get_by_owner(user["id"]):
            rows += records("market_cases", rid=business["id"], kind="Reclamo")
    rows = {c["id"]: c for c in rows}.values()
    for key, extract in (("estado", case_state), ("prioridad", lambda c:c.get("priority","Normal")),
                         ("fecha",lambda c:c["created"][:10]), ("usuario",lambda c:str(c["uid"])),
                         ("negocio",lambda c:str(c["rid"]))):
        selected = request.args.get(key)
        if selected:
            rows = [c for c in rows if extract(c) == selected]
    return render_template("communication/cases.html", cases=sorted(rows,key=lambda c:c["id"],reverse=True),
                           state=case_state, code=case_code, states=STATES, priorities=PRIORITIES)


@bp.get("/reclamos/<int:cid>")
def case_detail(cid):
    user = identity()
    case = Repo.get_by_id("market_cases", cid)
    case_access(case, user)
    staff = admins() if user["role"] == "admin" else []
    return render_template("communication/case.html", case=case, state=case_state(case), code=case_code(case),
                           events=records("case_history",cid=cid), staff=staff, states=STATES, priorities=PRIORITIES)


@bp.post("/reclamos/<int:cid>/analizar")
def analyze_case(cid):
    identity("admin")
    case = Repo.get_by_id("market_cases", cid)
    if not case or case.get("kind") != "Reclamo":
        abort(404)
    order = Repo.get_by_id("market_orders", case.get("oid")) if case.get("oid") else {}
    order = order or {}
    # No names, addresses, attachments or free-text from participants leave the server.
    facts = {"motivo":case.get("category","Otro"), "estado_reclamo":case_state(case),
             "estado_pedido":order.get("state"), "pagado":bool(order.get("paid")),
             "reembolso":bool(order.get("refunded")), "incidencia_pago":bool(order.get("payment_incident"))}
    suggestion = "Revisa la constancia y el estado del pago." if facts["motivo"] == "Pago" else "Contrasta el historial del pedido con la evidencia aportada."
    source = "Orientación por reglas"
    from utils.ia_qwen import obtener_respuesta_ia, QwenIAError
    from views.ai_routes import _rate_limited
    import json
    if _rate_limited():
        raise MarketError("Espera un momento antes de solicitar otro análisis.")
    try:
        response = obtener_respuesta_ia(json.dumps(facts, ensure_ascii=False),
            system_prompt="Ayuda a un moderador. Resume en dos frases los hechos estructurados y sugiere una comprobación. No inventes datos, no dictes una resolución.", max_tokens=160)
        if response and response.strip():
            suggestion, source = response.strip()[:1000], "Sugerencia del asistente"
    except QwenIAError:
        pass
    return render_template("communication/case.html", case=case, state=case_state(case), code=case_code(case),
                           events=records("case_history", cid=cid), staff=admins(), states=STATES,
                           priorities=PRIORITIES, suggestion=suggestion, source=source)


@bp.get("/reclamos/<int:cid>/archivo")
def case_file(cid):
    case = Repo.get_by_id("market_cases", cid)
    case_access(case, identity())
    return download(case.get("evidence"))


@bp.post("/reclamos/<int:cid>/actualizar")
def update_case(cid):
    user = identity("admin")
    state = request.form.get("state")
    priority = request.form.get("priority")
    assigned = integer(request.form.get("assigned"), 1)
    note = request.form.get("note", "").strip()
    if state not in STATES or priority not in PRIORITIES or not 5 <= len(note) <= 800:
        raise MarketError("Revisa el estado, la prioridad y la explicación de la decisión.")
    with document_transaction():
        case = Repo.get_by_id("market_cases", cid, for_update=True)
        case_access(case, user)
        if assigned not in [u["id"] for u in admins()]:
            raise MarketError("Selecciona un responsable activo de soporte.")
        current = case_state(case)
        terminal = {"Resuelto", "Rechazado con justificación"}
        if (current == "Cerrado" or STATES.index(state) < STATES.index(current)
                or current in terminal and state not in {current, "Cerrado"}
                or state == "Cerrado" and current not in terminal):
            raise MarketError("El reclamo no admite ese cambio de estado.")
        changes = {"assigned": assigned, "priority": priority, "state": state, "note": note}
        if state == "Cerrado":
            changes["closed"] = now().isoformat()
        updated = Repo.update("market_cases", cid, changes)
        case_event(updated, user["id"], note)
    return redirect(url_for("comunicacion.case_detail", cid=cid))


@bp.get("/notificaciones")
def notifications():
    uid = identity()["id"]
    archived = request.args.get('archivo') == '1'
    before = integer(request.args['antes'], 1) if request.args.get('antes') else None
    rows = NotificationModel.get_by_user(uid, limit=100, archived=archived, before=before)
    return render_template("communication/notifications.html", rows=rows, archived=archived,
                           next_before=rows[-1]['id'] if len(rows) == 100 else None)


@bp.post("/notificaciones/leer")
def read_notifications():
    uid = identity()["id"]
    nid = request.form.get("nid")
    if nid:
        if not NotificationModel.mark_as_read(uid, integer(nid, 1)):
            abort(404)
    else:
        NotificationModel.mark_all_as_read(uid)
    return redirect(url_for("comunicacion.notifications"))


@bp.post('/notificaciones/<int:nid>/<action>')
def notification_action(nid, action):
    if action not in {'archive', 'restore', 'delete'}:
        abort(404)
    if not NotificationModel.change_state(identity()['id'], nid, action):
        abort(404)
    return redirect(url_for('comunicacion.notifications', archivo=request.form.get('archivo', '0')))


@bp.get('/notificaciones/feed')
def notification_feed():
    # Transaction pooling cannot support LISTEN safely. This is explicitly periodic
    # reconciliation, not strict real-time SSE; no connection is held between reads.
    uid = identity()['id']
    with document_transaction():
        rows = NotificationModel.get_by_user(uid, limit=100)
        count = NotificationModel.get_unread_count(uid)
    response = jsonify(notifications=rows, unread_count=count)
    response.headers['Cache-Control'] = 'private, no-store'
    return response
