"""Private marketplace attachments, participant notifications and claim history."""
import base64
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from flask import Response

from database.repository import PostgresDocumentRepository as Repo
from logic.market import MarketError, now
from models.market import records
from models.notification import NotificationModel
from models.user import UserModel


STATES = ("Nuevo", "Pendiente", "En revisión", "En atención", "Resuelto", "Rechazado con justificación", "Cerrado")
PRIORITIES = ("Normal", "Alta", "Urgente")
REASONS = ("Pedido", "Entrega", "Calidad", "Pago", "Otro")


def admins():
    return [u for u in records("users", role="admin") if UserModel.is_active(u)]


def notify(recipients, title, message, link):
    for uid in set(recipients) - {None}:
        NotificationModel.create_notification(uid, title, message, link=link)


def attachment(file, rid=None):
    if not file or not file.filename:
        return None
    content = file.read(1024 * 1024 + 1)
    if not content or len(content) > 1024 * 1024:
        raise MarketError("El archivo debe pesar hasta 1 MB.")
    extension = "pdf"
    if not content.startswith(b"%PDF-"):
        try:
            with Image.open(BytesIO(content)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 12_000_000:
                    raise MarketError("Usa una imagen JPG, PNG o WebP de hasta 12 megapíxeles.")
                source.thumbnail((1600, 1600))
                clean = BytesIO()
                source.convert("RGB").save(clean, format="JPEG", quality=80)
                content = clean.getvalue()
                extension = "jpg"
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            raise MarketError("No se pudo leer el documento. Usa PDF, JPG, PNG o WebP.") from None
    return Repo.create("market_evidence", {"rid": rid, "extension": extension,
                       "content": base64.b64encode(content).decode("ascii")})["id"]


def download(evidence_id):
    from flask import abort
    item = Repo.get_by_id("market_evidence", evidence_id) if evidence_id else None
    if not item:
        abort(404)
    ext = "jpg" if item.get("extension") == "jpg" else "pdf"
    return Response(base64.b64decode(item["content"]), mimetype="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="evidencia.{ext}"',
                             "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


def case_state(case):
    return {"Abierto": "Nuevo", "Aceptado": "Cerrado", "Desestimado": "Cerrado"}.get(case["state"], case["state"])


def case_code(case):
    return f"SR-{case['id']:07d}"


def case_event(case, actor, note):
    Repo.create("case_history", {"cid": case["id"], "actor": actor, "state": case_state(case),
                "assigned": case.get("assigned"), "note": note, "created": now().isoformat()})
    owner = Repo.get_by_id("restaurants", case["rid"]) or {}
    recipients = {case["uid"], owner.get("owner_id"), case.get("assigned")}
    if case_state(case) == "Nuevo":
        recipients.update(u["id"] for u in admins())
    notify(recipients, f"Reclamo {case_code(case)}", f"Estado: {case_state(case)}.",
           f"/bandeja/reclamos/{case['id']}")
