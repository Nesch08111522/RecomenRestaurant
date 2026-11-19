"""Auditoría y cuota atómica en PostgreSQL; sin almacenar el texto de entrada."""

from __future__ import annotations
import json
from database.connection import connection
from utils.integrity import acquire_stream_lock, chain_head, digest_payload


def _decision_integrity_payload(row):
    """Return stable, non-hash fields for one persisted AI decision."""
    confidence = row["confianza"]
    created_at = row["created_at"]
    return {
        "id": int(row["id"]),
        "tipo": row["tipo"],
        "entidad": row["entidad"],
        "entidad_id": row["entidad_id"],
        "actor_user_id": int(row["actor_user_id"]),
        "entrada_resumida": row["entrada_resumida"],
        "entrada_hash": row["entrada_hash"],
        "salida_ia": row["salida_ia"],
        "modelo": row["modelo"],
        "confianza": format(confidence, "f") if confidence is not None else None,
        "decision_final_del_admin": row["decision_final_del_admin"],
        "aceptada_bool": row["aceptada_bool"],
        "latencia_ms": int(row["latencia_ms"]),
        "estado": row["estado"],
        "error_codigo": row["error_codigo"],
        "created_at": created_at.isoformat(),
        "integrity_sequence": int(row["integrity_sequence"]),
        "integrity_prev_hash": row["integrity_prev_hash"],
    }


def _set_decision_hash(cur, row):
    payload_hash = digest_payload(_decision_integrity_payload(row))
    cur.execute(
        "UPDATE public.ai_decisions SET integrity_payload_hash=%s WHERE id=%s",
        (payload_hash, row["id"]),
    )


class AIDecisionModel:
    @staticmethod
    def create(
        *,
        tipo,
        entidad,
        entidad_id,
        actor_user_id,
        entrada_resumida,
        entrada_hash,
        salida_ia=None,
        modelo=None,
        confianza=None,
        latencia_ms=0,
        estado="ok",
        error_codigo=None,
    ):
        if estado == "reserved":
            raise ValueError("Usa reserve() para crear una decisión pendiente.")
        with connection() as conn:
            with conn.cursor() as cur:
                acquire_stream_lock(cur, "ai_decisions")
                sequence, previous_hash = chain_head(cur, "ai_decisions")
                cur.execute(
                    """INSERT INTO public.ai_decisions
                    (tipo,entidad,entidad_id,actor_user_id,entrada_resumida,entrada_hash,salida_ia,
                     modelo,confianza,latencia_ms,estado,error_codigo,integrity_sequence,
                     integrity_prev_hash)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING *""",
                    (
                        tipo,
                        entidad,
                        entidad_id,
                        actor_user_id,
                        json.dumps(entrada_resumida),
                        entrada_hash,
                        (
                            json.dumps(salida_ia, ensure_ascii=False)
                            if salida_ia is not None
                            else None
                        ),
                        modelo,
                        confianza,
                        latencia_ms,
                        estado,
                        error_codigo,
                        sequence + 1,
                        previous_hash,
                    ),
                )
                result = cur.fetchone()
                _set_decision_hash(cur, result)
            conn.commit()
            return result["id"]

    @staticmethod
    def find_recent(*, actor_user_id, tipo, entrada_hash, model, seconds=600):
        with connection() as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT id,salida_ia,modelo,confianza FROM public.ai_decisions
                WHERE actor_user_id=%s AND tipo=%s AND entrada_hash=%s AND modelo=%s
                AND estado='ok' AND created_at > NOW()-(%s * INTERVAL '1 second')
                ORDER BY created_at DESC LIMIT 1""",
                (actor_user_id, tipo, entrada_hash, model, seconds),
            )
            return cur.fetchone()

    @staticmethod
    def reserve(*, actor_user_id, tipo, entrada_hash, limit=10):
        """Reserva una solicitud de manera atómica por administrador y minuto."""
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_advisory_xact_lock(%s,%s)", (74931, actor_user_id)
                )
                cur.execute(
                    """SELECT COUNT(*) AS total FROM public.ai_decisions
                    WHERE actor_user_id=%s AND estado='reserved'
                    AND created_at > NOW()-INTERVAL '1 minute'""",
                    (actor_user_id,),
                )
                if cur.fetchone()["total"] >= limit:
                    return None
                cur.execute(
                    """INSERT INTO public.ai_decisions
                    (tipo,entidad,actor_user_id,entrada_resumida,entrada_hash,estado)
                    VALUES (%s,'texto',%s,'{}'::jsonb,%s,'reserved') RETURNING id""",
                    (tipo, actor_user_id, entrada_hash),
                )
                reservation = cur.fetchone()["id"]
            conn.commit()
            return reservation

    @staticmethod
    def finish(
        decision_id,
        *,
        estado,
        entrada_resumida,
        salida_ia=None,
        modelo=None,
        confianza=None,
        latencia_ms=0,
        error_codigo=None,
        decision_final_del_admin=None,
        aceptada_bool=None,
    ):
        if estado == "reserved":
            raise ValueError("finish() requiere un estado final.")
        with connection() as conn:
            with conn.cursor() as cur:
                acquire_stream_lock(cur, "ai_decisions")
                sequence, previous_hash = chain_head(cur, "ai_decisions")
                cur.execute(
                    """UPDATE public.ai_decisions SET estado=%s,entrada_resumida=%s::jsonb,
                    salida_ia=%s::jsonb,modelo=%s,confianza=%s,latencia_ms=%s,error_codigo=%s,
                    decision_final_del_admin=COALESCE(%s,decision_final_del_admin),
                    aceptada_bool=COALESCE(%s,aceptada_bool),
                    integrity_sequence=%s,integrity_prev_hash=%s,integrity_payload_hash=NULL
                    WHERE id=%s AND estado='reserved' AND integrity_sequence IS NULL
                    RETURNING *""",
                    (
                        estado,
                        json.dumps(entrada_resumida),
                        (
                            json.dumps(salida_ia, ensure_ascii=False)
                            if salida_ia is not None
                            else None
                        ),
                        modelo,
                        confianza,
                        latencia_ms,
                        error_codigo,
                        decision_final_del_admin,
                        aceptada_bool,
                        sequence + 1,
                        previous_hash,
                        decision_id,
                    ),
                )
                result = cur.fetchone()
                if not result:
                    raise RuntimeError("Reserva de auditoría no encontrada")
                _set_decision_hash(cur, result)
            conn.commit()
