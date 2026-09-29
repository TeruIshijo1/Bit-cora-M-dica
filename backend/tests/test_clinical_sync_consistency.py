from __future__ import annotations

import ast
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

import clinical_sync
import clinical_sync_adapters
import database
import kh_database
import models


pytestmark = pytest.mark.postgresql


def _intent(session, key="test-key", operation_type="TEST_MUTATION"):
    return clinical_sync.create_or_get_intent(
        session,
        idempotency_key=key,
        operation_type=operation_type,
        aggregate_type="test",
        aggregate_id="aggregate-1",
        patient_ref="101",
        payload={"value": "safe"},
    )


def _locally_applied(session, key="test-key"):
    operation, created = _intent(session, key)
    assert created
    clinical_sync.mark_local_applied(session, operation)
    return operation


def _kh_operation(session, adapter: str, key: str):
    operation, created = clinical_sync.create_or_get_intent(
        session,
        idempotency_key=key,
        operation_type="KH_MUTATION",
        aggregate_type="clinical-test",
        aggregate_id=key,
        patient_ref="101",
        payload={"adapter": adapter, "args": ["101", {"value": key}], "kwargs": {}},
    )
    assert created
    clinical_sync.mark_local_applied(session, operation)
    return operation


def test_pg_success_and_external_success_is_synced():
    with database.SessionLocal() as session:
        operation = _locally_applied(session)
        result = clinical_sync.execute_external(
            session, operation, lambda: {"success": True}, session_factory=database.SessionLocal
        )
        assert result.state == clinical_sync.SYNCED
        session.refresh(operation)
        assert operation.local_applied_at and operation.external_applied_at
        assert operation.completed_at


def test_timeout_is_retryable_and_never_synced():
    with database.SessionLocal() as session:
        operation = _locally_applied(session)
        result = clinical_sync.execute_external(
            session,
            operation,
            lambda: (_ for _ in ()).throw(TimeoutError("network timeout")),
        )
        assert result.state == clinical_sync.RETRYABLE_ERROR
        assert operation.completed_at is None


def test_spanish_unavailable_message_is_retryable():
    assert clinical_sync.classify_external_error(
        RuntimeError("Vertical no disponible")
    ) is clinical_sync.RetryableExternalError


def test_permanent_external_error_is_failed():
    with database.SessionLocal() as session:
        operation = _locally_applied(session)
        result = clinical_sync.execute_external(
            session,
            operation,
            lambda: (_ for _ in ()).throw(ValueError("constraint violation")),
        )
        assert result.state == clinical_sync.FAILED


def test_legacy_error_dict_is_not_success():
    with database.SessionLocal() as session:
        operation = _locally_applied(session)
        result = clinical_sync.execute_external(
            session, operation, lambda: {"error": "constraint violation"}
        )
        assert result.state == clinical_sync.FAILED


def test_false_adapter_result_is_retryable():
    with database.SessionLocal() as session:
        operation = _locally_applied(session)
        result = clinical_sync.execute_external(session, operation, lambda: False)
        assert result.state == clinical_sync.RETRYABLE_ERROR


def test_unexpected_vertical_response_never_reports_success():
    with database.SessionLocal() as session:
        operation = _locally_applied(session, "unexpected-vertical")
        result = clinical_sync.execute_external(
            session, operation, lambda: {"d": {"Errors": []}}
        )
        assert result.state == clinical_sync.RETRYABLE_ERROR
        assert result.value is None


def test_same_idempotency_key_creates_one_operation():
    with database.SessionLocal() as session:
        first, first_created = _intent(session, "same-key")
        second, second_created = _intent(session, "same-key")
        assert first_created is True
        assert second_created is False
        assert first.operation_id == second.operation_id
        assert session.query(models.ClinicalSyncOperation).count() == 1


def test_fifty_concurrent_requests_create_one_intent():
    def create():
        with database.SessionLocal() as session:
            operation, created = _intent(session, "concurrent-key")
            return str(operation.operation_id), created

    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(lambda _: create(), range(50)))
    assert len({item[0] for item in results}) == 1
    assert sum(item[1] for item in results) == 1
    assert len(results) == 50


def test_restart_before_external_write_leaves_recoverable_pending():
    with database.SessionLocal() as session:
        operation, _ = _intent(session, "restart-before")
        operation_id = operation.operation_id
    with database.SessionLocal() as restarted:
        operation = restarted.get(models.ClinicalSyncOperation, operation_id)
        assert operation.state == clinical_sync.PENDING
        assert operation.external_applied_at is None


def test_reconciler_never_delivers_intent_without_local_confirmation():
    calls = []
    with database.SessionLocal() as session:
        operation, _ = _intent(session, "restart-before-local")
        results = clinical_sync.reconcile(
            session,
            lambda _operation: lambda: calls.append("external") or {"success": True},
            operation_ids=[operation.operation_id],
        )
        assert results[0].state == clinical_sync.REQUIRES_RECONCILIATION
        assert calls == []


def test_retry_after_timeout_does_not_create_second_operation():
    effects = []
    with database.SessionLocal() as session:
        operation = _locally_applied(session, "retry-key")
        first = clinical_sync.execute_external(
            session, operation, lambda: (_ for _ in ()).throw(TimeoutError("timeout"))
        )
        assert first.state == clinical_sync.RETRYABLE_ERROR
        operation.next_attempt_at = clinical_sync.utcnow() - dt.timedelta(seconds=1)
        session.commit()
        second = clinical_sync.execute_external(
            session, operation, lambda: effects.append("effect") or {"success": True}
        )
        assert second.state == clinical_sync.SYNCED
        assert effects == ["effect"]
        assert session.query(models.ClinicalSyncOperation).count() == 1


def test_synced_retry_never_calls_adapter_again():
    calls = []
    with database.SessionLocal() as session:
        operation = _locally_applied(session, "synced-retry")
        clinical_sync.execute_external(
            session, operation, lambda: calls.append(1) or {"success": True}
        )
        result = clinical_sync.execute_external(
            session, operation, lambda: calls.append(2) or {"success": True}
        )
        assert result.idempotent is True
        assert calls == [1]


def test_external_success_and_pg_confirmation_failure_is_reconcilable(monkeypatch):
    with database.SessionLocal() as session:
        operation = _locally_applied(session, "confirmation-failure")
        operation_id = operation.operation_id

        def fail_confirmation(*_args, **_kwargs):
            raise RuntimeError("simulated PostgreSQL confirmation failure")

        monkeypatch.setattr(clinical_sync, "mark_synced", fail_confirmation)
        result = clinical_sync.execute_external(
            session,
            operation,
            lambda: {"success": True},
            session_factory=database.SessionLocal,
        )
        assert result.state == clinical_sync.REQUIRES_RECONCILIATION

    with database.SessionLocal() as verification:
        persisted = verification.get(models.ClinicalSyncOperation, operation_id)
        assert persisted.state == clinical_sync.REQUIRES_RECONCILIATION
        assert persisted.external_applied_at is not None


def test_every_delivery_attempt_is_recorded():
    with database.SessionLocal() as session:
        operation = _locally_applied(session, "attempt-log")
        clinical_sync.execute_external(
            session, operation, lambda: (_ for _ in ()).throw(TimeoutError("timeout"))
        )
        attempts = session.query(models.ClinicalSyncAttempt).filter_by(
            operation_id=operation.operation_id
        ).all()
        assert len(attempts) == 1
        assert attempts[0].outcome == clinical_sync.RETRYABLE_ERROR


@pytest.mark.parametrize(
    "secret",
    [
        "postgresql://user:password@host/db",
        "Password=topsecret;Server=kh",
        "Authorization=BearerSecret",
        "Bearer ey.secret.token",
        "fmd_template=raw-biometric-value",
    ],
)
def test_errors_never_store_connection_strings_or_secrets(secret):
    sanitized = clinical_sync.sanitize_error(f"failure {secret}")
    assert "topsecret" not in sanitized
    assert "raw-biometric-value" not in sanitized
    assert "ey.secret.token" not in sanitized
    assert "postgresql://" not in sanitized


def test_minimal_payload_drops_biometrics_and_tokens():
    clean = clinical_sync.minimal_payload(
        {"name": "drug", "fmd_template": "secret", "challenge_id": "nonce", "jwt": "token"}
    )
    assert clean == {"name": "drug"}


def test_audit_helper_has_no_hidden_commit():
    source = Path(__file__).resolve().parents[1].joinpath("main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "log_auditoria")
    calls = {ast.unparse(node.func) for node in ast.walk(helper) if isinstance(node, ast.Call)}
    assert "db.commit" not in calls
    assert "db.flush" in calls


def test_all_get_endpoints_are_free_of_session_writes():
    source = Path(__file__).resolve().parents[1].joinpath("main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"db.add", "db.delete", "db.commit", "db.flush", "conn.commit"}
    offenders = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators = [ast.unparse(item) for item in node.decorator_list]
        if not any(item.startswith("app.get(") for item in decorators):
            continue
        calls = {ast.unparse(item.func) for item in ast.walk(node) if isinstance(item, ast.Call)}
        sql_mutation = False
        for item in ast.walk(node):
            if not isinstance(item, ast.Call) or not isinstance(item.func, ast.Attribute):
                continue
            if item.func.attr != "execute" or not item.args:
                continue
            sql_arg = item.args[0]
            if isinstance(sql_arg, ast.Constant) and isinstance(sql_arg.value, str):
                sql_mutation = any(
                    token in sql_arg.value.upper()
                    for token in ("INSERT ", "UPDATE ", "DELETE ", "MERGE ")
                )
        if calls & forbidden or sql_mutation:
            offenders.append(node.name)
    assert offenders == []


@pytest.mark.parametrize(
    "adapter",
    [
        "save_or_update_nota_hospitalizacion",
        "save_patient_vitals_ptvs",
        "save_patient_allergy_ptal",
        "save_or_update_consentimiento_25",
        "sync_contact_to_ptcn",
    ],
)
def test_remaining_kh_flows_retry_without_duplicate_effect(monkeypatch, adapter):
    effects = set()
    calls = {"count": 0}

    def fake_adapter(*_args, operation_id=None, **_kwargs):
        calls["count"] += 1
        if operation_id in effects:
            return {"success": True, "idempotent": True}
        effects.add(operation_id)
        raise TimeoutError("timeout after external commit")

    monkeypatch.setitem(clinical_sync_adapters._KH_MUTATORS, adapter, fake_adapter)
    with database.SessionLocal() as session:
        operation = _kh_operation(session, adapter, f"retry-{adapter}")
        first = clinical_sync.execute_external(
            session, operation, clinical_sync_adapters.dispatcher(operation)
        )
        assert first.state == clinical_sync.RETRYABLE_ERROR
        operation.next_attempt_at = clinical_sync.utcnow() - dt.timedelta(seconds=1)
        session.commit()
        second = clinical_sync.execute_external(
            session, operation, clinical_sync_adapters.dispatcher(operation)
        )
        assert second.state == clinical_sync.SYNCED
        assert len(effects) == 1
        assert calls["count"] == 2


def test_nota_urgencias_success_reaches_synced(monkeypatch):
    monkeypatch.setitem(
        clinical_sync_adapters._KH_MUTATORS,
        "save_or_update_nota_urgencias",
        lambda *_args, **_kwargs: {"success": True},
    )
    with database.SessionLocal() as session:
        operation = _kh_operation(session, "save_or_update_nota_urgencias", "urg-success")
        result = clinical_sync.execute_external(
            session, operation, clinical_sync_adapters.dispatcher(operation)
        )
        assert result.state == clinical_sync.SYNCED


def test_nota_urgencias_ambiguous_timeout_requires_controlled_reconciliation(monkeypatch):
    calls = []

    def timeout_after_possible_write(*_args, **_kwargs):
        calls.append(1)
        raise TimeoutError("timeout after possible slot update")

    monkeypatch.setitem(
        clinical_sync_adapters._KH_MUTATORS,
        "save_or_update_nota_urgencias",
        timeout_after_possible_write,
    )
    with database.SessionLocal() as session:
        operation, _ = clinical_sync.create_or_get_intent(
            session,
            idempotency_key="urg-ambiguous-timeout",
            operation_type="KH_MUTATION",
            aggregate_type="clinical-test",
            aggregate_id="101:urgency",
            patient_ref="101",
            payload={
                "adapter": "save_or_update_nota_urgencias",
                "args": ["101", {"fecha": "2026-09-17", "hora": "10:00"}],
                "kwargs": {},
                "retry_policy": "manual",
            },
        )
        clinical_sync.mark_local_applied(session, operation)
        first = clinical_sync.execute_external(
            session, operation, clinical_sync_adapters.dispatcher(operation)
        )
        assert first.state == clinical_sync.REQUIRES_RECONCILIATION
        results = clinical_sync.reconcile(
            session,
            clinical_sync_adapters.dispatcher,
            operation_ids=[operation.operation_id],
        )
        assert results[0].state == clinical_sync.REQUIRES_RECONCILIATION
        assert calls == [1]


def test_consent_timeout_never_reports_synced(monkeypatch):
    monkeypatch.setitem(
        clinical_sync_adapters._KH_MUTATORS,
        "save_or_update_consentimiento_25",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("SQL timeout")),
    )
    with database.SessionLocal() as session:
        operation = _kh_operation(session, "save_or_update_consentimiento_25", "consent-timeout")
        result = clinical_sync.execute_external(
            session, operation, clinical_sync_adapters.dispatcher(operation)
        )
        assert result.state == clinical_sync.RETRYABLE_ERROR
        assert result.state != clinical_sync.SYNCED


@pytest.mark.parametrize("operation_type", ["UNIVERSAL_FORMAT_CREATE", "UNIVERSAL_FORMAT_UPDATE"])
def test_universal_format_dispatch_is_retry_safe(monkeypatch, operation_type):
    effects = set()

    def fake_universal(patient_ref, document, operation_id=None):
        key = operation_id or f"{patient_ref}:{document.get('mrnum')}"
        already = key in effects
        effects.add(key)
        return {"success": True, "mrnum": document.get("mrnum") or 77, "idempotent": already}

    if operation_type == "UNIVERSAL_FORMAT_CREATE":
        monkeypatch.setattr(clinical_sync_adapters, "_universal_format_create", fake_universal)
    else:
        monkeypatch.setattr(
            clinical_sync_adapters,
            "_universal_format_update",
            lambda patient_ref, document: fake_universal(patient_ref, document),
        )
    with database.SessionLocal() as session:
        operation, _ = clinical_sync.create_or_get_intent(
            session,
            idempotency_key=f"universal-{operation_type}",
            operation_type=operation_type,
            aggregate_type="universal",
            aggregate_id="101:FMT:77",
            patient_ref="101",
            payload={"document": {"codigo": "FMT", "mrnum": 77}},
        )
        clinical_sync.mark_local_applied(session, operation)
        result = clinical_sync.execute_external(
            session, operation, clinical_sync_adapters.dispatcher(operation)
        )
        assert result.state == clinical_sync.SYNCED
        assert len(effects) == 1


def test_universal_create_without_safe_guid_stays_manual(monkeypatch):
    calls = []

    def blocked(*_args, **_kwargs):
        calls.append(1)
        raise clinical_sync.ManualReconciliationRequired("sin GUID seguro")

    monkeypatch.setattr(clinical_sync_adapters, "_universal_format_create", blocked)
    with database.SessionLocal() as session:
        operation, _ = clinical_sync.create_or_get_intent(
            session,
            idempotency_key="universal-manual",
            operation_type="UNIVERSAL_FORMAT_CREATE",
            aggregate_type="universal",
            aggregate_id="101:FMT:0",
            patient_ref="101",
            payload={"document": {"codigo": "FMT"}, "retry_policy": "manual"},
        )
        clinical_sync.mark_local_applied(session, operation)
        first = clinical_sync.execute_external(
            session, operation, clinical_sync_adapters.dispatcher(operation)
        )
        assert first.state == clinical_sync.REQUIRES_RECONCILIATION
        results = clinical_sync.reconcile(
            session,
            clinical_sync_adapters.dispatcher,
            operation_ids=[operation.operation_id],
        )
        assert results[0].state == clinical_sync.REQUIRES_RECONCILIATION
        assert calls == [1]


def test_every_decorated_kh_mutator_has_a_durable_strategy():
    source = Path(kh_database.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    decorated = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and any(isinstance(item, ast.Name) and item.id == "explicit_kh_mutation" for item in node.decorator_list)
    }
    assert decorated <= set(clinical_sync_adapters.MUTATOR_STRATEGIES)
    assert set(clinical_sync_adapters._KH_MUTATORS) <= set(clinical_sync_adapters.MUTATOR_STRATEGIES)


def test_all_direct_clinical_kh_mutations_are_routed_through_durable_helpers():
    source = Path(__file__).resolve().parents[1].joinpath("main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = set(clinical_sync_adapters._KH_MUTATORS) | {
        "save_patient_medication_ptdg",
        "discontinue_patient_medication_ptdg",
        "save_patient_diet_mr_sol_diet",
    }
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id == "kh_database"
            and function.attr in forbidden
        ):
            offenders.append(function.attr)
    assert offenders == []


def test_universal_endpoints_enter_durable_path_before_sql_server_code():
    source = Path(__file__).resolve().parents[1].joinpath("main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {"create_universal_format_record", "update_or_save_universal_format_record"}
    for function in (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names):
        calls = [ast.unparse(node.func) for node in ast.walk(function) if isinstance(node, ast.Call)]
        assert "_durable_universal_format_write" in calls


def test_reconciler_dispatcher_supports_every_operation_type(monkeypatch):
    monkeypatch.setattr(clinical_sync_adapters, "_patient_discharge", lambda *_: {"success": True})
    monkeypatch.setattr(clinical_sync_adapters, "_patient_readmission", lambda *_: {"success": True})
    samples = [
        ("MEDICATION_PRESCRIBE", {"medication": {}}),
        ("MEDICATION_DISCONTINUE", {"ptdg_num": 1}),
        ("DIET_PRESCRIBE", {"diet": {}}),
        ("PATIENT_DISCHARGE", {}),
        ("PATIENT_READMISSION", {}),
        ("VERTICAL_SIGN", {"controller_name": "MR_X", "mrnum": 1, "doctor_name": "D"}),
        ("UNIVERSAL_FORMAT_CREATE", {"document": {"codigo": "X"}}),
        ("UNIVERSAL_FORMAT_UPDATE", {"document": {"codigo": "X", "mrnum": 1}}),
        ("KH_MUTATION", {"adapter": "sync_contact_to_ptcn", "args": ["101", {}], "kwargs": {}}),
    ]
    for operation_type, payload in samples:
        operation = SimpleNamespace(
            operation_type=operation_type,
            operation_id="00000000-0000-0000-0000-000000000001",
            patient_ref="101",
            payload=payload,
        )
        assert callable(clinical_sync_adapters.dispatcher(operation))
