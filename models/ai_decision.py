"""Auditoría y cuota atómica en PostgreSQL; sin almacenar el texto de entrada."""

from __future__ import annotations
import json
from database.connection import connection


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
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO public.ai_decisions
                    (tipo,entidad,entidad_id,actor_user_id,entrada_resumida,entrada_hash,salida_ia,
                     modelo,confianza,latencia_ms,estado,error_codigo)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s,%s,%s,%s,%s) RETURNING id""",
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
                    ),
                )
                result = cur.fetchone()["id"]
            conn.commit()
            return result

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
    ):
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE public.ai_decisions SET estado=%s,entrada_resumida=%s::jsonb,
                    salida_ia=%s::jsonb,modelo=%s,confianza=%s,latencia_ms=%s,error_codigo=%s
                    WHERE id=%s AND estado='reserved' RETURNING id""",
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
                        decision_id,
                    ),
                )
                if not cur.fetchone():
                    raise RuntimeError("Reserva de auditoría no encontrada")
            conn.commit()
