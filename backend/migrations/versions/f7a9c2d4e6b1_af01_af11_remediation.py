"""AF-01..AF-11 security and integrity remediation

Revision ID: f7a9c2d4e6b1
Revises: d4f5a6b7c8d9
Create Date: 2026-09-17 18:00:00
"""

from typing import Sequence, Union
import hashlib
import json

from alembic import op
import sqlalchemy as sa


revision: str = "f7a9c2d4e6b1"
down_revision: Union[str, Sequence[str], None] = "d4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clinical_sync_operations",
        sa.Column("request_fingerprint", sa.String(64), nullable=True),
    )
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT operation_id, operation_type, aggregate_type, aggregate_id, "
        "patient_ref, payload FROM clinical_sync_operations "
        "WHERE request_fingerprint IS NULL"
    )).mappings()
    for row in rows:
        material = json.dumps(
            {
                "operation_type": row["operation_type"],
                "aggregate_type": row["aggregate_type"],
                "aggregate_id": str(row["aggregate_id"]),
                "patient_ref": str(row["patient_ref"]) if row["patient_ref"] is not None else None,
                "payload": row["payload"] or {},
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest()
        connection.execute(
            sa.text(
                "UPDATE clinical_sync_operations SET request_fingerprint = :fingerprint "
                "WHERE operation_id = :operation_id"
            ),
            {"fingerprint": fingerprint, "operation_id": row["operation_id"]},
        )
    op.alter_column("clinical_sync_operations", "request_fingerprint", nullable=False)

    op.add_column(
        "medicos",
        sa.Column("biometric_reenrolled_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "medicos",
        sa.Column("biometric_reenrolled_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_medicos_biometric_reenrolled_by",
        "medicos",
        "usuarios",
        ["biometric_reenrolled_by_id"],
        ["id"],
    )

    op.add_column(
        "biometric_challenges",
        sa.Column("acquisition_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_biometric_challenges_acquisition_id",
        "biometric_challenges",
        ["acquisition_id"],
        unique=True,
    )

    # Preserve existing evidence while closing any pre-existing duplicate active
    # rows before installing the invariant. The newest row remains active.
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY COALESCE(pt_num, ''), COALESCE(codigo_formato, ''),
                                    COALESCE(evolution_slot, -1),
                                    COALESCE(rol_firmante, 'MEDICO'),
                                    COALESCE(document_version, '')
                       ORDER BY fecha_hora_firma DESC NULLS LAST, id DESC
                   ) AS rn
              FROM firmas_documentos_clinicos
             WHERE estado = 'ACTIVA'
        )
        UPDATE firmas_documentos_clinicos f
           SET estado = 'HISTORICA',
               fecha_revocacion = COALESCE(fecha_revocacion, CURRENT_TIMESTAMP),
               motivo_revocacion = COALESCE(
                   motivo_revocacion,
                   'Normalización previa a unicidad de firma activa AF-05'
               )
          FROM ranked r
         WHERE f.id = r.id AND r.rn > 1
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_firma_documento_activa_logica
            ON firmas_documentos_clinicos (
                COALESCE(pt_num, ''),
                COALESCE(codigo_formato, ''),
                COALESCE(evolution_slot, -1),
                COALESCE(rol_firmante, 'MEDICO'),
                COALESCE(document_version, '')
            )
         WHERE estado = 'ACTIVA'
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
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_firma_evidence_immutable
        BEFORE UPDATE ON firmas_documentos_clinicos
        FOR EACH ROW EXECUTE FUNCTION hes_protect_completed_signature_evidence()
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION hes_prevent_completed_signature_delete()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.canonical_payload IS NOT NULL OR OLD.signature_schema_version = 'CANONICAL_V2' THEN
                RAISE EXCEPTION 'La evidencia de una firma completada no puede eliminarse';
            END IF;
            RETURN OLD;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_firma_evidence_no_delete
        BEFORE DELETE ON firmas_documentos_clinicos
        FOR EACH ROW EXECUTE FUNCTION hes_prevent_completed_signature_delete()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_firma_evidence_no_delete ON firmas_documentos_clinicos")
    op.execute("DROP FUNCTION IF EXISTS hes_prevent_completed_signature_delete()")
    op.execute("DROP TRIGGER IF EXISTS trg_firma_evidence_immutable ON firmas_documentos_clinicos")
    op.execute("DROP FUNCTION IF EXISTS hes_protect_completed_signature_evidence()")
    op.execute("DROP INDEX IF EXISTS uq_firma_documento_activa_logica")
    op.drop_index("ix_biometric_challenges_acquisition_id", table_name="biometric_challenges")
    op.drop_column("biometric_challenges", "acquisition_id")
    op.drop_constraint("fk_medicos_biometric_reenrolled_by", "medicos", type_="foreignkey")
    op.drop_column("medicos", "biometric_reenrolled_at")
    op.drop_column("medicos", "biometric_reenrolled_by_id")
    op.drop_column("clinical_sync_operations", "request_fingerprint")
