from config import _environment_int
from utils.integrity_scheduler import (
    run_integrity_cycle,
    should_start_integrity_worker,
)


def test_scheduler_is_disabled_for_tests_and_reloader_parent():
    enabled_config = {
        "INTEGRITY_AUTO_ENABLED": True,
        "INTEGRITY_INTERVAL_SECONDS": 300,
        "INTEGRITY_BATCH_SIZE": 500,
    }

    assert not should_start_integrity_worker({**enabled_config, "TESTING": True}, {})
    assert not should_start_integrity_worker(
        {**enabled_config, "DEBUG": True},
        {"WERKZEUG_RUN_MAIN": "false"},
    )
    assert not should_start_integrity_worker(
        {**enabled_config, "DEBUG": False},
        {"PYTEST_CURRENT_TEST": "test_integrity_scheduler.py"},
    )
    assert should_start_integrity_worker(
        {**enabled_config, "DEBUG": False},
        {},
    )


def test_integrity_interval_has_ten_second_minimum(monkeypatch):
    monkeypatch.setenv("INTEGRITY_INTERVAL_SECONDS", "1")
    assert _environment_int("INTEGRITY_INTERVAL_SECONDS", 300, minimum=10) == 10


def test_integrity_cycle_runs_verification_when_signing_fails(monkeypatch):
    calls = []

    def fail_signing(*, batch_size):
        calls.append(("sign", batch_size))
        raise OSError("database unavailable")

    def verify():
        calls.append(("verify",))
        return [], 0

    monkeypatch.setattr("scripts.integrity_audit.sign_pending_roots", fail_signing)
    monkeypatch.setattr("scripts.integrity_audit.verify_integrity", verify)

    run_integrity_cycle(batch_size=25)

    assert calls == [("sign", 25), ("verify",)]


def test_app_startup_configures_worker_without_database(monkeypatch):
    from app import create_app

    calls = []
    monkeypatch.setattr("config.Config.validate", lambda: None)
    monkeypatch.setattr("database.connection.check_application_schema", lambda: None)
    monkeypatch.setattr(
        "utils.integrity_scheduler.start_integrity_worker",
        lambda app_config: calls.append(
            (
                app_config["INTEGRITY_AUTO_ENABLED"],
                app_config["INTEGRITY_INTERVAL_SECONDS"],
                app_config["INTEGRITY_BATCH_SIZE"],
            )
        ),
    )

    create_app(
        {
            "TESTING": False,
            "INTEGRITY_AUTO_ENABLED": True,
            "INTEGRITY_INTERVAL_SECONDS": 45,
            "INTEGRITY_BATCH_SIZE": 75,
        }
    )

    assert calls == [(True, 45, 75)]
