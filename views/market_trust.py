"""Human review of marketplace evidence and service complaints."""
from collections import Counter
from datetime import datetime

from flask import abort, redirect, render_template, request, url_for

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import MarketError, now
from models.market import indicators, private_evidence, records
from models.communication import admins, case_event, case_state, download, notify
from views.market import identity, market_bp
from views.market_kitchen import authorize, return_desk


@market_bp.post("/cocina/<int:rid>/acreditar")
def submit_evidence(rid):
    authorize(rid, owner_only=True)
    file = request.files.get("document")
    with document_transaction():
        evidence = private_evidence(rid, file)
        case = Repo.create("market_cases", {"rid": rid, "uid": identity()["id"], "kind": "Acreditación",
                    "reason": "Documento presentado por el titular", "evidence": evidence,
                    "created": now().isoformat(), "state": "Abierto"})
        notify([u["id"] for u in admins()], "Solicitud de acreditación", f"Expediente #{case['id']}.",
               url_for("market.trust"))
    return return_desk(rid, "Documento enviado a revisión privada.")


@market_bp.get("/confianza")
def trust():
    identity("admin")
    orders = Repo.all("market_orders")
    offers = Repo.all("market_offers")
    cases = Repo.all("market_cases")
    hashes = Counter(o["photo_hash"] for o in offers if o.get("photo_hash"))
    alerts = [o for o in offers if hashes.get(o.get("photo_hash"), 0) > 1]
    cancels = Counter(o["rid"] for o in orders if o["state"] == "Cancelado")
    visits = Repo.all("market_views")
    funnel = {stage: sum(bool(v.get(stage)) for v in visits) for stage in ("viewed", "clicked", "ordered")}
    closed = [c for c in cases if c.get("closed")]
    review_hours = [max(0, (datetime.fromisoformat(c["closed"]) - datetime.fromisoformat(c["created"])).total_seconds()) / 3600 for c in closed]
    signals = [c for c in closed if c["kind"] == "Señal de revisión"]
    durations = [o["draft_seconds"] for o in offers if o.get("draft_seconds") is not None]
    return render_template("market/trust.html", cases=cases[::-1], alerts=alerts, metrics=indicators(orders),
                           review_hours=round(sum(review_hours)/len(review_hours),1) if review_hours else None,
                           signal_count=len(signals), dismissed=sum(c["state"]=="Desestimado" for c in signals),
                           publish_minutes=round(sum(durations)/len(durations)/60,1) if durations else None,
                           cancels=[(rid, n) for rid, n in cancels.items() if n >= 3],
                           funnel=funnel, classified=sum(bool(o.get("vision_used")) for o in offers),
                           accepted=sum(bool(o.get("vision_accepted")) for o in offers))


@market_bp.post("/confianza/senal/<int:rid>")
def open_signal(rid):
    admin = identity("admin")
    from models.market import lock_business
    with document_transaction():
        lock_business(rid)
        if not records("market_cases", rid=rid, kind="Señal de revisión", state="Abierto"):
            Repo.create("market_cases", {"rid": rid, "uid": admin["id"], "kind": "Señal de revisión",
                        "reason": "Comprobar coincidencias de fotos o patrón de cancelaciones.",
                        "state": "Abierto", "created": now().isoformat()})
    return redirect(url_for("market.trust"))


@market_bp.get("/confianza/<int:cid>/documento")
def evidence(cid):
    identity("admin")
    case = Repo.get_by_id("market_cases", cid)
    if not case or not case.get("evidence"):
        abort(404)
    return download(case["evidence"])


@market_bp.post("/confianza/<int:cid>")
def resolve(cid):
    admin = identity("admin")
    result = request.form.get("result")
    note = request.form.get("note", "").strip()
    if result not in {"Aceptado", "Desestimado"} or not 5 <= len(note) <= 800:
        raise MarketError("Selecciona una decisión y registra su motivo.")
    with document_transaction():
        case = Repo.get_by_id("market_cases", cid, for_update=True)
        if not case:
            abort(404)
        if case["kind"] == "Reclamo":
            if case_state(case) == "Cerrado":
                raise MarketError("Este expediente ya tiene una decisión.")
            case = Repo.update("market_cases", cid, {"state": "Cerrado", "decision": result, "note": note,
                               "actor": admin["id"], "closed": now().isoformat()})
            case_event(case, admin["id"], note)
            return redirect(url_for("comunicacion.case_detail", cid=cid))
        if case["state"] != "Abierto":
            raise MarketError("Este expediente ya tiene una decisión.")
        Repo.update("market_cases", cid, {"state": result, "note": note, "actor": admin["id"], "closed": now().isoformat()})
        notify([case["uid"]], "Decisión del expediente", f"{case['kind']}: {result}.", url_for("market.desk",rid=case["rid"]))
    return redirect(url_for("market.trust"))

