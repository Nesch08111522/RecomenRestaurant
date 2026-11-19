"""Account protection backed by the same transaction store as user identities."""
import base64
import hashlib
import hmac
import re
import secrets
import struct
import time

from cryptography.fernet import Fernet
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from models.user import UserModel


def digest(purpose, value):
    key = current_app.secret_key.encode()
    return hmac.digest(key, (purpose + "\0" + value).encode(), "sha256")


def password_valid(value):
    return 8 <= len(value) <= 256 and re.search(r"[a-zA-Z]", value) and re.search(r"\d", value)


def allow_attempt(action, username, address):
    """Reserve an attempt atomically for the account and the originating address."""
    with document_transaction() as conn:
        now = int(time.time())
        for scope, value, limit in (("ip", address, 80), ("account", username, 12)):
            identifier = -1 - (int.from_bytes(digest(action + scope, value)[:8], "big") >> 1)
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (identifier,))
            row = Repo.get_by_id("auth_limits", identifier)
            fresh = not row or now - row["since"] >= 600
            count = 0 if fresh else row["count"]
            if count >= limit:
                if count == limit:
                    from models.communication import admins, notify
                    from utils.audit import record_event
                    record_event("ACCOUNT_RATE_LIMIT", resource_type="seguridad", metadata={"scope":scope, "operation":action})
                    notify([u["id"] for u in admins()], "Acceso temporalmente limitado",
                           "Se alcanzó el límite de intentos. Consulta la auditoría de seguridad.", "/admin/controles")
                    Repo.update("auth_limits", identifier, {"count": count + 1})
                return False
            state = {"since": now if fresh else row["since"], "count": count + 1}
            if row:
                Repo.update("auth_limits", identifier, state)
            else:
                Repo.create("auth_limits", {"id": identifier, **state})
        if secrets.randbelow(64) == 0:
            conn.execute("DELETE FROM public.app_records WHERE collection='auth_limits' AND updated_at < now() - interval '1 day'")
        return True


def cipher():
    return Fernet(base64.urlsafe_b64encode(digest("account-encryption", "v1")))


def totp(secret, counter):
    raw = hmac.digest(base64.b32decode(secret), struct.pack(">Q", counter), "sha1")
    offset = raw[-1] & 15
    return f"{(int.from_bytes(raw[offset:offset+4], 'big') & 0x7fffffff) % 1000000:06d}"


def matching_counter(encrypted, token, previous=-1):
    if not encrypted or not re.fullmatch(r"[0-9]{6}", token):
        return None
    secret = cipher().decrypt(encrypted.encode()).decode()
    now = int(time.time() // 30)
    return next((n for n in (now, now - 1, now + 1) if n > previous and hmac.compare_digest(totp(secret, n), token)), None)


def authenticate(username, password, token):
    with document_transaction():
        user = UserModel.authenticate(username, password)
        if not user:
            return None
        state = Repo.get_by_id("account_security", user["id"], for_update=True) or {}
        if state.get("active"):
            counter = matching_counter(state["active"], token, state.get("last_counter", -1))
            if counter is None:
                return None
            Repo.update("account_security", user["id"], {"last_counter": counter})
        return user


def configure(uid, password, action, token, *, email=None, phone=None):
    with document_transaction():
        user = Repo.get_by_id("users", uid, for_update=True)
        if not UserModel.is_active(user) or not check_password_hash(user["password"], password):
            raise ValueError("Verifica la contraseña actual.")
        state = Repo.get_by_id("account_security", uid, for_update=True)
        if not state:
            state = Repo.create("account_security", {"id": uid})
        if state.get("active"):
            counter = matching_counter(state["active"], token, state.get("last_counter", -1))
            if counter is None:
                raise ValueError("Introduce un código nuevo del autenticador.")
            Repo.update("account_security", uid, {"last_counter": counter})
        if action == "contacts":
            email=str(email or '').strip().lower();phone=str(phone or '').strip()
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or '\r' in email or '\n' in email:
                raise ValueError("Revisa el correo de recuperación.")
            if phone and not re.fullmatch(r'\+[1-9]\d{7,14}',phone):
                raise ValueError("Usa un teléfono internacional, por ejemplo +51976399537.")
            profile={**(user.get('profile') or {}),'email':email,'phone':phone}
            epoch=user.get('auth_epoch',0)+1
            Repo.update('users',uid,{'profile':profile,'auth_epoch':epoch})
            from utils.audit import record_event
            record_event('SECURITY_CONTACTS_CHANGED',resource_type='cuenta',resource_id=uid)
            return {'epoch':epoch,'contacts_saved':True}
        if action == "recovery":
            code = secrets.token_urlsafe(24)
            Repo.update("account_security", uid, {"recovery": digest("recovery", code).hex()})
            return {"code": code}
        if action == "start" and not state.get("active"):
            secret = base64.b32encode(secrets.token_bytes(20)).decode()
            Repo.update("account_security", uid, {"pending": cipher().encrypt(secret.encode()).decode(), "until": time.time() + 600})
            return {"secret": secret}
        if action == "enable" and not state.get("active") and state.get("until", 0) > time.time():
            counter = matching_counter(state.get("pending"), token)
            if counter is not None:
                code = secrets.token_urlsafe(24)
                Repo.update("account_security", uid, {"active": state["pending"], "pending": None, "last_counter": counter,
                                                      "recovery": digest("recovery", code).hex()})
                Repo.update("users", uid, {"auth_epoch": user.get("auth_epoch", 0) + 1})
                from utils.audit import record_event
                record_event("ACCOUNT_MFA_ENABLED", resource_type="cuenta", resource_id=uid)
                return {"code": code, "epoch": user.get("auth_epoch", 0) + 1}
        raise ValueError("Revisa el código y el plazo de activación.")


def reset_password(username, code, password):
    if len(code) > 128:
        return False
    with document_transaction():
        user = UserModel.get_by_username(username)
        if not UserModel.is_active(user):
            return False
        uid = user["id"]
        user = Repo.get_by_id("users", uid, for_update=True)
        state = Repo.get_by_id("account_security", uid, for_update=True) or {}
        if not UserModel.is_active(user) or not hmac.compare_digest(state.get("recovery") or "", digest("recovery", code).hex()):
            return False
        Repo.update("users", uid, {"password": generate_password_hash(password), "auth_epoch": user.get("auth_epoch", 0) + 1})
        Repo.update("account_security", uid, {"recovery": None, "active": None, "pending": None})
        from utils.audit import record_event
        record_event("ACCOUNT_RECOVERED", resource_type="cuenta", resource_id=uid, actor_user_id=uid)
        return True
