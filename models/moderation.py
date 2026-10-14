from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config import Config
from models.base import JSONModel
from utils.content_filter import ContentFilter


APPROVAL_AUTOMATIC = "APROBADO_AUTOMATICAMENTE"
APPROVAL_PENDING = "PENDIENTE_REVISION"
APPROVAL_REJECTED = "RECHAZADO"
APPROVAL_SUSPENDED = "SUSPENDIDO"
APPROVAL_STATES = {APPROVAL_AUTOMATIC, APPROVAL_PENDING, APPROVAL_REJECTED, APPROVAL_SUSPENDED}
LEGACY_TO_CONTROLLED = {
    "pending": APPROVAL_PENDING,
    "approved": APPROVAL_AUTOMATIC,
    "rejected": APPROVAL_REJECTED,
    "suspended": APPROVAL_SUSPENDED,
}
CONTROLLED_TO_LEGACY = {
    APPROVAL_AUTOMATIC: "approved",
    APPROVAL_PENDING: "pending",
    APPROVAL_REJECTED: "rejected",
    APPROVAL_SUSPENDED: "suspended",
}


class ModerationModel(JSONModel):
    """Moderación trazable y reversible, con compatibilidad para JSON legacy."""

    file_path = Config.MODERATION_FILE

    @classmethod
    def normalize_state(cls, entry: dict[str, Any]) -> str:
        value = str(entry.get("approval_status") or entry.get("status") or "pending").upper()
        if value in APPROVAL_STATES:
            return value
        return LEGACY_TO_CONTROLLED.get(str(entry.get("status", "pending")).lower(), APPROVAL_PENDING)

    @classmethod
    def get_pending_reviews(cls):
        return [item for item in cls._load_data() if cls.normalize_state(item) == APPROVAL_PENDING]

    @classmethod
    def get_flagged_content(cls):
        return [item for item in cls._load_data() if item.get("flagged", False)]

    @classmethod
    def preliminary_evaluate(cls, content_type: str, content_data: dict[str, Any]) -> dict[str, Any]:
        """Evaluación preliminar determinista; no constituye una decisión humana.

        Se guarda evidencia de reglas y datos evaluados. La aprobación automática
        solo se propone para contenido completo, culinario y sin señales críticas.
        Cualquier señal grave deja la decisión final en revisión humana.
        """
        content_data = content_data if isinstance(content_data, dict) else {}
        text = " ".join(str(content_data.get(field, "")) for field in ("name", "description", "category"))
        tags = content_data.get("tags", [])
        if isinstance(tags, list):
            text = f"{text} {' '.join(str(tag) for tag in tags)}"
        result = ContentFilter.check_content(text)
        required = ["name", "description", "category"] if content_type == "restaurant" else ["name", "description"]
        missing = [field for field in required if not str(content_data.get(field, "")).strip()]
        issues = list(result.get("suggestions", []))
        if missing:
            issues.append(f"Campos requeridos ausentes: {', '.join(missing)}")
        critical = bool(result.get("banned_words"))
        complete_and_clean = not missing and result.get("is_appropriate", False) and result.get("is_food_related", False)
        if complete_and_clean:
            verdict = APPROVAL_AUTOMATIC
            final_status = APPROVAL_AUTOMATIC
            confidence = 0.90
        elif critical:
            verdict = APPROVAL_REJECTED
            # El rechazo del prechequeo no bloquea la revisión humana.
            final_status = APPROVAL_PENDING
            confidence = 0.85
        else:
            verdict = APPROVAL_PENDING
            final_status = APPROVAL_PENDING
            confidence = 0.55
        return {
            "model_version": "content-filter-rules-v1",
            "content_type": content_type,
            "ai_verdict": verdict,
            "final_status": final_status,
            "confidence": confidence,
            "rules": {
                "required_fields": required,
                "missing_fields": missing,
                "critical_signal": critical,
                "food_score": result.get("food_score", 0),
                "banned_words": result.get("banned_words", []),
                "food_words_found": result.get("food_words_found", []),
            },
            "issues": issues,
            "human_review_required": final_status == APPROVAL_PENDING,
        }

    @classmethod
    def create_moderation_entry(cls, content_type, content_id, content_data, user_id, reason="", ai_evaluation=None):
        evaluation = ai_evaluation or cls.preliminary_evaluate(content_type, content_data)
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "content_type": content_type,
            "content_id": content_id,
            "content_data": content_data if isinstance(content_data, dict) else {},
            "user_id": user_id,
            "reason": reason,
            "status": CONTROLLED_TO_LEGACY[evaluation["final_status"]],
            "approval_status": evaluation["final_status"],
            "ai_verdict": evaluation.get("ai_verdict"),
            "ai_confidence": evaluation.get("confidence"),
            "ai_evaluation": evaluation,
            "decision_source": "AI_PRECHECK",
            "flagged": bool(evaluation.get("rules", {}).get("critical_signal") or evaluation.get("issues")),
            "flags": [],
            "reversible": True,
            "status_history": [{
                "from": None,
                "to": evaluation["final_status"],
                "actor_user_id": None,
                "source": "AI_PRECHECK",
                "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
                "timestamp": now,
            }],
            "created_at": now,
            "updated_at": now,
        }
        return cls.create(entry)

    @classmethod
    def flag_content(cls, moderation_id, flag_type, reason):
        entry = cls.get_by_id(moderation_id)
        if not entry:
            return None
        flags = list(entry.get("flags", []))
        flags.append({"type": str(flag_type)[:60], "reason": str(reason)[:500], "timestamp": datetime.now(timezone.utc).isoformat()})
        entry["flags"] = flags
        entry["flagged"] = True
        return cls.update(moderation_id, entry)

    @classmethod
    def transition_status(cls, moderation_id: int, new_status: str, *, actor_user_id: int | None = None, notes: str = "", source: str = "ADMIN_REVIEW"):
        if new_status not in APPROVAL_STATES:
            raise ValueError("Estado de aprobación no permitido")
        entry = cls.get_by_id(moderation_id)
        if not entry:
            return None
        previous = cls.normalize_state(entry)
        now = datetime.now(timezone.utc).isoformat()
        history = list(entry.get("status_history", []))
        history.append({
            "from": previous,
            "to": new_status,
            "actor_user_id": actor_user_id,
            "source": source,
            "notes": str(notes or "")[:1000],
            "timestamp": now,
        })
        entry.update({
            "approval_status": new_status,
            "status": CONTROLLED_TO_LEGACY[new_status],
            "decision_source": source,
            "admin_notes": str(notes or "")[:1000],
            "status_history": history,
            "updated_at": now,
        })
        if source == "ADMIN_REVIEW":
            entry["human_decision_by"] = actor_user_id
            entry["human_decision_at"] = now
        return cls.update(moderation_id, entry)

    @classmethod
    def approve_content(cls, moderation_id, admin_notes="", actor_user_id=None):
        return cls.transition_status(moderation_id, APPROVAL_AUTOMATIC, actor_user_id=actor_user_id, notes=admin_notes)

    @classmethod
    def reject_content(cls, moderation_id, admin_notes="", actor_user_id=None):
        return cls.transition_status(moderation_id, APPROVAL_REJECTED, actor_user_id=actor_user_id, notes=admin_notes)

    @classmethod
    def suspend_content(cls, moderation_id, admin_notes="", actor_user_id=None):
        return cls.transition_status(moderation_id, APPROVAL_SUSPENDED, actor_user_id=actor_user_id, notes=admin_notes)

    @classmethod
    def revert_content(cls, moderation_id, target_status=APPROVAL_PENDING, admin_notes="", actor_user_id=None):
        return cls.transition_status(moderation_id, target_status, actor_user_id=actor_user_id, notes=admin_notes, source="ADMIN_REVERT")

    @classmethod
    def get_stats(cls):
        data = cls._load_data()
        counts = {state: 0 for state in APPROVAL_STATES}
        for item in data:
            counts[cls.normalize_state(item)] += 1
        return {
            "total": len(data),
            "pending": counts[APPROVAL_PENDING],
            "approved": counts[APPROVAL_AUTOMATIC],
            "rejected": counts[APPROVAL_REJECTED],
            "suspended": counts[APPROVAL_SUSPENDED],
            "flagged": sum(1 for item in data if item.get("flagged", False)),
            "by_controlled_status": counts,
        }


from datetime import datetime, timezone
from typing import Any

from config import Config
from models.base import JSONModel
from utils.content_filter import ContentFilter, AUTO_OK, HUMAN, ASK_AI

APPROVAL_AUTOMATIC = "APROBADO_AUTOMATICAMENTE"
APPROVAL_PENDING = "PENDIENTE_REVISION"
APPROVAL_REJECTED = "RECHAZADO"
APPROVAL_SUSPENDED = "SUSPENDIDO"

APPROVAL_STATES = {
    APPROVAL_AUTOMATIC,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    APPROVAL_SUSPENDED,
}

LEGACY_TO_CONTROLLED = {
    "pending": APPROVAL_PENDING,
    "approved": APPROVAL_AUTOMATIC,
    "rejected": APPROVAL_REJECTED,
    "suspended": APPROVAL_SUSPENDED,
}

CONTROLLED_TO_LEGACY = {
    APPROVAL_AUTOMATIC: "approved",
    APPROVAL_PENDING: "pending",
    APPROVAL_REJECTED: "rejected",
    APPROVAL_SUSPENDED: "suspended",
}


class ModerationModel(JSONModel):
    """Moderación trazable, reversible y compatible con registros antiguos."""

    file_path = Config.MODERATION_FILE

    @classmethod
    def normalize_state(cls, entry: dict[str, Any]) -> str:
        value = str(
            entry.get("approval_status") or entry.get("status") or "pending"
        ).upper()

        if value in APPROVAL_STATES:
            return value

        legacy = str(entry.get("status") or "pending").lower()
        return LEGACY_TO_CONTROLLED.get(legacy, APPROVAL_PENDING)

    @classmethod
    def get_pending_reviews(cls):
        return [
            item
            for item in cls._load_data()
            if cls.normalize_state(item) == APPROVAL_PENDING
        ]

    @classmethod
    def get_flagged_content(cls):
        return [item for item in cls._load_data() if item.get("flagged", False)]

    @classmethod
    def preliminary_evaluate(
        cls,
        content_type: str,
        content_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evalúa contenido sin simular una decisión de IA externa.

        AUTO_OK: contenido culinario reconocido, completo y limpio.
        HUMAN: lenguaje grave, etiquetas inapropiadas o evasión.
        ASK_AI: idioma desconocido, contexto dudoso o datos insuficientes.

        HUMAN y ASK_AI quedan pendientes de revisión; no se rechazan
        definitivamente sin una decisión administrativa.
        """
        data = content_data if isinstance(content_data, dict) else {}

        if content_type == "restaurant":
            filtered = ContentFilter.filter_restaurant(data)
            result = filtered["result"]
            missing = filtered["missing_fields"]
            issues = list(filtered["issues"])
            route = filtered["route"]

            # Incluye las etiquetas en la evidencia de evaluación.
            tag_results = filtered.get("tags", [])
            inappropriate_tags = [
                tag["tag"] for tag in tag_results if not tag.get("is_appropriate", True)
            ]

            if inappropriate_tags:
                route = HUMAN

        else:
            fields = ("name", "description", "category")
            text_parts = [str(data.get(field) or "") for field in fields]

            tags = data.get("tags") or []
            if isinstance(tags, list):
                text_parts.extend(str(tag) for tag in tags)

            result = ContentFilter.check_content(" ".join(text_parts))

            required = ["name", "description"]
            missing = [
                field for field in required if not str(data.get(field) or "").strip()
            ]

            issues = list(result.get("issues", []))
            route = ContentFilter.triage(result, missing)

        # Las notas son informativas y no deben convertirse en incidencias.
        banned_words = list(result.get("banned_words", []))
        context_words = list(result.get("context_words", []))
        evasion = bool(result.get("evasion_suspected", False))

        if route == AUTO_OK:
            verdict = APPROVAL_AUTOMATIC
            final_status = APPROVAL_AUTOMATIC
            confidence = 0.90
        elif route == HUMAN:
            verdict = APPROVAL_REJECTED
            final_status = APPROVAL_PENDING
            confidence = 0.85
        else:  # ASK_AI
            verdict = APPROVAL_PENDING
            final_status = APPROVAL_PENDING
            confidence = 0.55

        critical_signal = bool(banned_words or evasion)

        return {
            "model_version": "content-filter-rules-v2",
            "content_type": content_type,
            "route": route,
            "ai_verdict": verdict,
            "final_status": final_status,
            "confidence": confidence,
            "rules": {
                "required_fields": (
                    ["name", "description"]
                    if content_type == "restaurant"
                    else ["name", "description"]
                ),
                "missing_fields": missing,
                "critical_signal": critical_signal,
                "evasion_suspected": evasion,
                "dictionary_can_judge": result.get("dictionary_can_judge", False),
                "food_score": result.get("food_score", 0),
                "banned_words": banned_words,
                "context_words": context_words,
                "food_words_found": result.get("food_words_found", []),
                "coverage": result.get("coverage", {}),
                "inappropriate_tags": (
                    inappropriate_tags if content_type == "restaurant" else []
                ),
            },
            "issues": issues,
            "notes": list(result.get("notes", [])),
            "human_review_required": route in (HUMAN, ASK_AI),
        }

    @classmethod
    def create_moderation_entry(
        cls,
        content_type,
        content_id,
        content_data,
        user_id,
        reason="",
        ai_evaluation=None,
    ):
        evaluation = ai_evaluation or cls.preliminary_evaluate(
            content_type, content_data
        )

        final_status = evaluation.get("final_status", APPROVAL_PENDING)
        if final_status not in APPROVAL_STATES:
            final_status = APPROVAL_PENDING

        now = datetime.now(timezone.utc).isoformat()
        rules = evaluation.get("rules", {})

        entry = {
            "content_type": content_type,
            "content_id": content_id,
            "content_data": (content_data if isinstance(content_data, dict) else {}),
            "user_id": user_id,
            "reason": reason,
            "status": CONTROLLED_TO_LEGACY[final_status],
            "approval_status": final_status,
            "ai_verdict": evaluation.get("ai_verdict"),
            "ai_confidence": evaluation.get("confidence"),
            "ai_evaluation": evaluation,
            "decision_source": "AI_PRECHECK",
            "flagged": bool(
                evaluation.get("human_review_required") or evaluation.get("issues")
            ),
            "flags": [],
            "reversible": True,
            "status_history": [
                {
                    "from": None,
                    "to": final_status,
                    "actor_user_id": None,
                    "source": "AI_PRECHECK",
                    "notes": (
                        "Preevaluación automática; no sustituye "
                        "la revisión administrativa."
                    ),
                    "timestamp": now,
                }
            ],
            "created_at": now,
            "updated_at": now,
        }

        return cls.create(entry)

    @classmethod
    def flag_content(cls, moderation_id, flag_type, reason):
        entry = cls.get_by_id(moderation_id)
        if not entry:
            return None

        flags = list(entry.get("flags") or [])
        flags.append(
            {
                "type": str(flag_type)[:60],
                "reason": str(reason)[:500],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        entry["flags"] = flags
        entry["flagged"] = True
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()

        return cls.update(moderation_id, entry)

    @classmethod
    def transition_status(
        cls,
        moderation_id: int,
        new_status: str,
        *,
        actor_user_id: int | None = None,
        notes: str = "",
        source: str = "ADMIN_REVIEW",
    ):
        if new_status not in APPROVAL_STATES:
            raise ValueError("Estado de aprobación no permitido")

        entry = cls.get_by_id(moderation_id)
        if not entry:
            return None

        previous = cls.normalize_state(entry)
        now = datetime.now(timezone.utc).isoformat()
        history = list(entry.get("status_history") or [])

        history.append(
            {
                "from": previous,
                "to": new_status,
                "actor_user_id": actor_user_id,
                "source": source,
                "notes": str(notes or "")[:1000],
                "timestamp": now,
            }
        )

        entry.update(
            {
                "approval_status": new_status,
                "status": CONTROLLED_TO_LEGACY[new_status],
                "decision_source": source,
                "admin_notes": str(notes or "")[:1000],
                "status_history": history,
                "updated_at": now,
            }
        )

        if source == "ADMIN_REVIEW":
            entry["human_decision_by"] = actor_user_id
            entry["human_decision_at"] = now

        return cls.update(moderation_id, entry)

    @classmethod
    def approve_content(cls, moderation_id, admin_notes="", actor_user_id=None):
        return cls.transition_status(
            moderation_id,
            APPROVAL_AUTOMATIC,
            actor_user_id=actor_user_id,
            notes=admin_notes,
        )

    @classmethod
    def reject_content(cls, moderation_id, admin_notes="", actor_user_id=None):
        return cls.transition_status(
            moderation_id,
            APPROVAL_REJECTED,
            actor_user_id=actor_user_id,
            notes=admin_notes,
        )

    @classmethod
    def suspend_content(cls, moderation_id, admin_notes="", actor_user_id=None):
        return cls.transition_status(
            moderation_id,
            APPROVAL_SUSPENDED,
            actor_user_id=actor_user_id,
            notes=admin_notes,
        )

    @classmethod
    def revert_content(
        cls,
        moderation_id,
        target_status=APPROVAL_PENDING,
        admin_notes="",
        actor_user_id=None,
    ):
        return cls.transition_status(
            moderation_id,
            target_status,
            actor_user_id=actor_user_id,
            notes=admin_notes,
            source="ADMIN_REVERT",
        )

    @classmethod
    def get_stats(cls):
        data = cls._load_data()
        counts = {state: 0 for state in APPROVAL_STATES}

        for item in data:
            counts[cls.normalize_state(item)] += 1

        return {
            "total": len(data),
            "pending": counts[APPROVAL_PENDING],
            "approved": counts[APPROVAL_AUTOMATIC],
            "rejected": counts[APPROVAL_REJECTED],
            "suspended": counts[APPROVAL_SUSPENDED],
            "flagged": sum(1 for item in data if item.get("flagged", False)),
            "by_controlled_status": counts,
        }
