from models.moderation import (
    APPROVAL_AUTOMATIC,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    ModerationModel,
)


def test_preliminary_evaluation_does_not_auto_reject_critical_content(tmp_path, monkeypatch):
    monkeypatch.setattr(ModerationModel, "file_path", str(tmp_path / "moderation.json"))
    evaluation = ModerationModel.preliminary_evaluate(
        "restaurant",
        {"name": "Restaurante", "description": "violencia en el plato", "category": "criollo"},
    )
    assert evaluation["ai_verdict"] == APPROVAL_REJECTED
    assert evaluation["final_status"] == APPROVAL_PENDING
    assert evaluation["human_review_required"] is True


def test_admin_transition_is_reversible_and_keeps_history(tmp_path, monkeypatch):
    monkeypatch.setattr(ModerationModel, "file_path", str(tmp_path / "moderation.json"))
    entry = ModerationModel.create_moderation_entry(
        "restaurant",
        10,
        {"name": "Casa Criolla", "description": "comida criolla tradicional", "category": "criollo"},
        2,
    )
    assert ModerationModel.normalize_state(entry) == APPROVAL_AUTOMATIC
    rejected = ModerationModel.reject_content(entry["id"], "Revisión manual", actor_user_id=1)
    assert rejected["approval_status"] == APPROVAL_REJECTED
    reverted = ModerationModel.revert_content(entry["id"], APPROVAL_PENDING, "Solicitar documentación", actor_user_id=1)
    assert reverted["approval_status"] == APPROVAL_PENDING
    assert len(reverted["status_history"]) == 3
    assert reverted["status_history"][-1]["source"] == "ADMIN_REVERT"
