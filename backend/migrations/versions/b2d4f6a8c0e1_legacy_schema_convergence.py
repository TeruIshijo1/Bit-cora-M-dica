"""Converge unversioned legacy installations without deleting clinical data.

Revision ID: b2d4f6a8c0e1
Revises: 9e2c4b6d8f10
Create Date: 2026-09-21 09:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b2d4f6a8c0e1"
down_revision: Union[str, Sequence[str], None] = "9e2c4b6d8f10"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table)}


def _foreign_keys(table: str) -> set[str]:
    return {item.get("name") for item in sa.inspect(op.get_bind()).get_foreign_keys(table)}


def _unique_constraints(table: str) -> set[str]:
    return {item.get("name") for item in sa.inspect(op.get_bind()).get_unique_constraints(table)}


def _add_column(table: str, name: str, column: sa.Column) -> None:
    if name not in _columns(table):
        op.add_column(table, column)


def _add_index(name: str, table: str, columns, *, unique: bool = False) -> None:
    if name not in _indexes(table):
        op.create_index(name, table, columns, unique=unique)


def _add_foreign_key(name: str, source: str, target: str, local, remote, **kwargs) -> None:
    if name not in _foreign_keys(source):
        op.create_foreign_key(name, source, target, local, remote, **kwargs)


def _ensure_identity_and_biometric_fields() -> None:
    _add_column(
        "usuarios", "must_change_password",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _add_column("medicos", "private_key_cipher_version", sa.Column("private_key_cipher_version", sa.String(64)))
    op.execute(
        "UPDATE medicos SET private_key_cipher_version = 'FERNET_HKDF_SHA256_V1' "
        "WHERE private_key_enc IS NOT NULL AND private_key_cipher_version IS NULL"
    )
    _add_column("medicos", "biometric_reenrolled_by_id", sa.Column("biometric_reenrolled_by_id", sa.Integer()))
    _add_column("medicos", "biometric_reenrolled_at", sa.Column("biometric_reenrolled_at", sa.DateTime()))
    _add_foreign_key(
        "fk_medicos_biometric_reenrolled_by", "medicos", "usuarios",
        ["biometric_reenrolled_by_id"], ["id"],
    )
    _add_column(
        "biometric_challenges", "expected_identity_ref",
        sa.Column("expected_identity_ref", sa.String(128)),
    )
    _add_column(
        "biometric_challenges", "acquisition_id",
        sa.Column("acquisition_id", sa.String(128)),
    )
    _add_index(
        "ix_biometric_challenges_expected_identity_ref", "biometric_challenges",
        ["expected_identity_ref"],
    )
    _add_index(
        "ix_biometric_challenges_acquisition_id", "biometric_challenges",
        ["acquisition_id"], unique=True,
    )
    if not _unique_constraints("biometric_challenges"):
        if "ix_biometric_challenges_token_hash" in _indexes("biometric_challenges"):
            op.execute(
                "ALTER TABLE biometric_challenges ADD CONSTRAINT "
                "biometric_challenges_token_hash_key UNIQUE USING INDEX ix_biometric_challenges_token_hash"
            )
        else:
            op.create_unique_constraint(
                "biometric_challenges_token_hash_key", "biometric_challenges", ["token_hash"]
            )


def _ensure_key_and_signature_evidence() -> None:
    key_id_added = "key_id" not in _columns("historial_llaves_fea")
    _add_column("historial_llaves_fea", "key_id", sa.Column("key_id", sa.String(64)))
    _add_column(
        "historial_llaves_fea", "estado",
        sa.Column("estado", sa.String(32), nullable=False, server_default="ACTIVA"),
    )
    if key_id_added:
        op.execute("UPDATE historial_llaves_fea SET key_id = 'legacy-' || id::text WHERE key_id IS NULL")
    else:
        op.execute("UPDATE historial_llaves_fea SET key_id = 'legacy-' || id::text WHERE key_id IS NULL")
    op.execute(
        "UPDATE historial_llaves_fea SET estado = CASE WHEN activo THEN 'ACTIVA' ELSE 'INACTIVA' END "
        "WHERE estado IS NULL OR estado NOT IN ('ACTIVA', 'INACTIVA')"
    )
    op.alter_column("historial_llaves_fea", "key_id", existing_type=sa.String(64), nullable=False)
    _add_index("ix_historial_llaves_fea_key_id", "historial_llaves_fea", ["key_id"], unique=True)
    if "uq_historial_llaves_fea_unica_activa" not in _indexes("historial_llaves_fea"):
        op.execute("""
            WITH ranked AS (
                SELECT id, row_number() OVER (
                    PARTITION BY medico_id ORDER BY fecha_creacion DESC NULLS LAST, id DESC
                ) AS rn
                FROM historial_llaves_fea WHERE activo IS TRUE
            )
            UPDATE historial_llaves_fea h
               SET activo = FALSE,
                   estado = 'INACTIVA',
                   fecha_inactivacion = COALESCE(fecha_inactivacion, CURRENT_TIMESTAMP)
              FROM ranked r WHERE h.id = r.id AND r.rn > 1
        """)
        op.create_index(
            "uq_historial_llaves_fea_unica_activa", "historial_llaves_fea", ["medico_id"],
            unique=True, postgresql_where=sa.text("activo IS TRUE"),
        )

    signature_columns = (
        ("key_id", sa.Column("key_id", sa.String(64))),
        ("signature_schema_version", sa.Column("signature_schema_version", sa.String(32), nullable=False, server_default="LEGACY_V1")),
        ("canonical_payload", sa.Column("canonical_payload", sa.Text())),
        ("payload_hash", sa.Column("payload_hash", sa.String(64))),
        ("document_version", sa.Column("document_version", sa.String(128))),
        ("pdf_hash", sa.Column("pdf_hash", sa.String(64))),
        ("pdf_identifier", sa.Column("pdf_identifier", sa.String(255))),
        ("tsa_status", sa.Column("tsa_status", sa.String(32), nullable=False, server_default="SIN_TSA")),
        ("tsa_nonce", sa.Column("tsa_nonce", sa.String(128))),
        ("tsa_attempts", sa.Column("tsa_attempts", sa.Integer(), nullable=False, server_default="0")),
        ("tsa_last_error", sa.Column("tsa_last_error", sa.Text())),
        ("tsa_verified_at", sa.Column("tsa_verified_at", sa.DateTime())),
    )
    for name, column in signature_columns:
        _add_column("firmas_documentos_clinicos", name, column)
    op.execute(
        "UPDATE firmas_documentos_clinicos SET tsa_status = "
        "CASE WHEN tsa_token IS NULL THEN 'SIN_TSA' ELSE 'TSA_LEGACY_NO_VERIFICADO' END "
        "WHERE tsa_status IS NULL OR tsa_status = 'SIN_TSA'"
    )
    _add_index("ix_firmas_documentos_clinicos_key_id", "firmas_documentos_clinicos", ["key_id"])
    _add_index(
        "ix_firmas_documentos_clinicos_signature_schema_version",
        "firmas_documentos_clinicos", ["signature_schema_version"],
    )
    _add_index("ix_firmas_documentos_clinicos_tsa_status", "firmas_documentos_clinicos", ["tsa_status"])
    _add_foreign_key(
        "fk_firmas_documentos_key_id", "firmas_documentos_clinicos", "historial_llaves_fea",
        ["key_id"], ["key_id"],
    )


def _ensure_clinical_sync() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("clinical_sync_operations"):
        op.create_table(
            "clinical_sync_operations",
            sa.Column("operation_id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("idempotency_key", sa.String(255), nullable=False),
            sa.Column("operation_type", sa.String(80), nullable=False),
            sa.Column("aggregate_type", sa.String(80), nullable=False),
            sa.Column("aggregate_id", sa.String(255), nullable=False),
            sa.Column("patient_ref", sa.String(80)),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("request_fingerprint", sa.String(64), nullable=False),
            sa.Column("state", sa.String(32), nullable=False, server_default="PENDING"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("last_error", sa.Text()),
            sa.Column("local_applied_at", sa.DateTime(timezone=True)),
            sa.Column("external_applied_at", sa.DateTime(timezone=True)),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            sa.CheckConstraint(
                "state IN ('PENDING','PROCESSING','SYNCED','RETRYABLE_ERROR','FAILED','REQUIRES_RECONCILIATION')",
                name="ck_clinical_sync_operation_state",
            ),
            sa.UniqueConstraint("idempotency_key", name="uq_clinical_sync_idempotency_key"),
        )
    elif "request_fingerprint" not in _columns("clinical_sync_operations"):
        op.add_column("clinical_sync_operations", sa.Column("request_fingerprint", sa.String(64)))
        op.execute(
            "UPDATE clinical_sync_operations SET request_fingerprint = "
            "encode(digest(operation_type || ':' || aggregate_type || ':' || aggregate_id || ':' || "
            "COALESCE(patient_ref, '') || ':' || payload::text, 'sha256'), 'hex') "
            "WHERE request_fingerprint IS NULL"
        )
        op.alter_column("clinical_sync_operations", "request_fingerprint", nullable=False)
    for name, columns in (
        ("ix_clinical_sync_operations_operation_type", ["operation_type"]),
        ("ix_clinical_sync_operations_aggregate_id", ["aggregate_id"]),
        ("ix_clinical_sync_operations_patient_ref", ["patient_ref"]),
        ("ix_clinical_sync_operations_state", ["state"]),
        ("ix_clinical_sync_operations_next_attempt_at", ["next_attempt_at"]),
        ("idx_clinical_sync_reconciliation", ["state", "next_attempt_at", "created_at"]),
    ):
        _add_index(name, "clinical_sync_operations", columns)

    if not sa.inspect(op.get_bind()).has_table("clinical_sync_attempts"):
        op.create_table(
            "clinical_sync_attempts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("outcome", sa.String(32), nullable=False),
            sa.Column("error_class", sa.String(120)),
            sa.Column("error_message", sa.Text()),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["operation_id"], ["clinical_sync_operations.operation_id"], ondelete="CASCADE"),
            sa.UniqueConstraint("operation_id", "attempt_number", name="uq_clinical_sync_attempt_number"),
        )
    _add_index("ix_clinical_sync_attempts_operation_id", "clinical_sync_attempts", ["operation_id"])

    for table in ("firmas_documentos_clinicos", "historico_notas_clinicas", "dieta_cuidados_prescripciones"):
        _add_column(
            table, "clinical_sync_operation_id",
            sa.Column("clinical_sync_operation_id", postgresql.UUID(as_uuid=True)),
        )
        _add_foreign_key(
            f"fk_{table}_clinical_sync_operation", table, "clinical_sync_operations",
            ["clinical_sync_operation_id"], ["operation_id"],
        )
        _add_index(
            f"ix_{table}_clinical_sync_operation_id", table,
            ["clinical_sync_operation_id"], unique=True,
        )


def _ensure_audit_and_revocation() -> None:
    # A current installation already has the append-only trigger. Temporarily
    # remove it inside this transaction so only legacy NULLs can be backfilled;
    # _ensure_invariants recreates it before commit.
    op.execute("DROP TRIGGER IF EXISTS trg_auditoria_logs_append_only ON auditoria_logs")
    for name, column in (
        ("request_id", sa.Column("request_id", sa.String(128))),
        ("operation_id", sa.Column("operation_id", sa.String(128))),
        ("actor_real", sa.Column("actor_real", sa.String(255))),
        ("actor_effective", sa.Column("actor_effective", sa.String(255))),
        ("motivo_impersonacion", sa.Column("motivo_impersonacion", sa.String(500))),
        ("resultado", sa.Column("resultado", sa.String(32))),
    ):
        _add_column("auditoria_logs", name, column)
    op.execute("""
        UPDATE auditoria_logs
           SET request_id = COALESCE(request_id, 'legacy-' || id::text),
               actor_real = COALESCE(actor_real, CASE WHEN usuario_id IS NULL THEN 'sistema' ELSE 'usuario:' || usuario_id::text END),
               actor_effective = COALESCE(actor_effective, CASE WHEN usuario_id IS NULL THEN 'sistema' ELSE 'usuario:' || usuario_id::text END),
               resultado = COALESCE(resultado, 'LEGACY')
    """)
    for name in ("request_id", "actor_real", "actor_effective", "resultado", "accion"):
        op.alter_column("auditoria_logs", name, nullable=False)
    _add_index("ix_auditoria_logs_request_id", "auditoria_logs", ["request_id"])
    _add_index("ix_auditoria_logs_operation_id", "auditoria_logs", ["operation_id"])

    if not sa.inspect(op.get_bind()).has_table("revoked_tokens"):
        op.create_table(
            "revoked_tokens",
            sa.Column("jti", sa.String(64), primary_key=True),
            sa.Column("subject", sa.String(255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("reason", sa.String(255), nullable=False, server_default="LOGOUT"),
            sa.Column("revoked_by", sa.String(255)),
        )
    _add_index("ix_revoked_tokens_subject", "revoked_tokens", ["subject"])
    _add_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def _ensure_invariants() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION protect_historial_llaves_fea()
        RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'historial_llaves_fea es append-only'; END IF;
          IF NEW.id IS DISTINCT FROM OLD.id OR NEW.key_id IS DISTINCT FROM OLD.key_id
             OR NEW.medico_id IS DISTINCT FROM OLD.medico_id
             OR NEW.public_key_pem IS DISTINCT FROM OLD.public_key_pem
             OR NEW.fecha_creacion IS DISTINCT FROM OLD.fecha_creacion THEN
            RAISE EXCEPTION 'material histórico FEA inmutable';
          END IF;
          IF OLD.activo IS NOT TRUE OR NEW.activo IS NOT FALSE
             OR OLD.fecha_inactivacion IS NOT NULL OR NEW.fecha_inactivacion IS NULL
             OR NEW.estado <> 'INACTIVA' THEN
            RAISE EXCEPTION 'transición de estado FEA no permitida';
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        DROP TRIGGER IF EXISTS trg_protect_historial_llaves_fea ON historial_llaves_fea;
        CREATE TRIGGER trg_protect_historial_llaves_fea
        BEFORE UPDATE OR DELETE ON historial_llaves_fea
        FOR EACH ROW EXECUTE FUNCTION protect_historial_llaves_fea();
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION hes_block_auditoria_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'auditoria_logs es append-only'; END; $$;
        DROP TRIGGER IF EXISTS trg_auditoria_logs_append_only ON auditoria_logs;
        CREATE TRIGGER trg_auditoria_logs_append_only
        BEFORE UPDATE OR DELETE ON auditoria_logs
        FOR EACH ROW EXECUTE FUNCTION hes_block_auditoria_mutation();
    """)
    if "uq_firma_documento_activa_logica" not in _indexes("firmas_documentos_clinicos"):
        op.execute("""
            WITH ranked AS (
                SELECT id, row_number() OVER (
                    PARTITION BY COALESCE(pt_num, ''), COALESCE(codigo_formato, ''),
                                 COALESCE(evolution_slot, -1), COALESCE(rol_firmante, 'MEDICO'),
                                 COALESCE(document_version, '')
                    ORDER BY fecha_hora_firma DESC NULLS LAST, id DESC
                ) AS rn
                FROM firmas_documentos_clinicos WHERE estado = 'ACTIVA'
            )
            UPDATE firmas_documentos_clinicos f
               SET estado = 'HISTORICA', fecha_revocacion = COALESCE(fecha_revocacion, CURRENT_TIMESTAMP),
                   motivo_revocacion = COALESCE(motivo_revocacion, 'Normalización previa a unicidad de firma activa')
              FROM ranked r WHERE f.id = r.id AND r.rn > 1
        """)
        op.execute("""
            CREATE UNIQUE INDEX uq_firma_documento_activa_logica
            ON firmas_documentos_clinicos (
                COALESCE(pt_num, ''), COALESCE(codigo_formato, ''), COALESCE(evolution_slot, -1),
                COALESCE(rol_firmante, 'MEDICO'), COALESCE(document_version, '')
            ) WHERE estado = 'ACTIVA'
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION hes_protect_completed_signature_evidence()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.canonical_payload IS NOT NULL OR OLD.signature_schema_version = 'CANONICAL_V2' THEN
                IF NEW.canonical_payload IS DISTINCT FROM OLD.canonical_payload
                   OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash
                   OR NEW.hash_sha256 IS DISTINCT FROM OLD.hash_sha256
                   OR NEW.sello_digital IS DISTINCT FROM OLD.sello_digital
                   OR NEW.cadena_original IS DISTINCT FROM OLD.cadena_original
                   OR NEW.key_id IS DISTINCT FROM OLD.key_id
                   OR NEW.pt_num IS DISTINCT FROM OLD.pt_num
                   OR NEW.expediente IS DISTINCT FROM OLD.expediente
                   OR NEW.codigo_formato IS DISTINCT FROM OLD.codigo_formato
                   OR NEW.tipo_documento IS DISTINCT FROM OLD.tipo_documento
                   OR NEW.evolution_slot IS DISTINCT FROM OLD.evolution_slot
                   OR NEW.document_version IS DISTINCT FROM OLD.document_version
                   OR NEW.signature_schema_version IS DISTINCT FROM OLD.signature_schema_version
                   OR NEW.rol_firmante IS DISTINCT FROM OLD.rol_firmante
                   OR NEW.firmante_id IS DISTINCT FROM OLD.firmante_id
                   OR NEW.medico_id IS DISTINCT FROM OLD.medico_id
                   OR NEW.pdf_hash IS DISTINCT FROM OLD.pdf_hash
                   OR NEW.pdf_identifier IS DISTINCT FROM OLD.pdf_identifier THEN
                    RAISE EXCEPTION 'La evidencia de una firma completada es inmutable';
                END IF;
            END IF;
            RETURN NEW;
        END; $$;
        DROP TRIGGER IF EXISTS trg_firma_evidence_immutable ON firmas_documentos_clinicos;
        CREATE TRIGGER trg_firma_evidence_immutable BEFORE UPDATE ON firmas_documentos_clinicos
        FOR EACH ROW EXECUTE FUNCTION hes_protect_completed_signature_evidence();
        CREATE OR REPLACE FUNCTION hes_prevent_completed_signature_delete()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.canonical_payload IS NOT NULL OR OLD.signature_schema_version = 'CANONICAL_V2' THEN
                RAISE EXCEPTION 'La evidencia de una firma completada no puede eliminarse';
            END IF;
            RETURN OLD;
        END; $$;
        DROP TRIGGER IF EXISTS trg_firma_evidence_no_delete ON firmas_documentos_clinicos;
        CREATE TRIGGER trg_firma_evidence_no_delete BEFORE DELETE ON firmas_documentos_clinicos
        FOR EACH ROW EXECUTE FUNCTION hes_prevent_completed_signature_delete();
    """)


def upgrade() -> None:
    _ensure_identity_and_biometric_fields()
    _ensure_key_and_signature_evidence()
    _ensure_clinical_sync()
    _ensure_audit_and_revocation()
    _ensure_invariants()
    _add_index("ix_catalogo_formatos_codigo", "catalogo_formatos", ["codigo"])
    _add_index("ix_catalogo_formatos_id", "catalogo_formatos", ["id"])
    _add_index("ix_pacientes_codigo_barras", "pacientes", ["codigo_barras"])
    _add_index("ix_firmas_documentos_clinicos_estado", "firmas_documentos_clinicos", ["estado"])
    _add_index("ix_firmas_documentos_clinicos_rol_firmante", "firmas_documentos_clinicos", ["rol_firmante"])
    op.alter_column("catalogo_formatos", "codigo", existing_type=sa.String(), nullable=False)
    op.alter_column("catalogo_formatos", "nombre", existing_type=sa.String(), nullable=False)
    op.alter_column(
        "medicos", "fmd_template", existing_type=sa.String(), type_=sa.Text(), existing_nullable=True
    )
    # Some legacy dumps contain orphaned historical references. NOT VALID keeps
    # those rows recoverable while enforcing referential integrity for new data.
    if "auditoria_logs_usuario_id_fkey" not in _foreign_keys("auditoria_logs"):
        op.execute(
            "ALTER TABLE auditoria_logs ADD CONSTRAINT auditoria_logs_usuario_id_fkey "
            "FOREIGN KEY (usuario_id) REFERENCES usuarios(id) NOT VALID"
        )
    if "traslados_pacientes_paciente_id_fkey" not in _foreign_keys("traslados_pacientes"):
        op.execute(
            "ALTER TABLE traslados_pacientes ADD CONSTRAINT traslados_pacientes_paciente_id_fkey "
            "FOREIGN KEY (paciente_id) REFERENCES pacientes(id) NOT VALID"
        )


def downgrade() -> None:
    # Recovery must use the verified pre-migration backup. Destructive downgrade
    # is deliberately omitted to preserve clinical and cryptographic evidence.
    pass
