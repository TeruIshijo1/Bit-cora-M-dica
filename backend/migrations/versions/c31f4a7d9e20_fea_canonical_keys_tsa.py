"""canonical clinical signatures, exact key ids and verified TSA state

Revision ID: c31f4a7d9e20
Revises: 4b7e2a91c6d0
Create Date: 2026-09-17 20:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c31f4a7d9e20"
down_revision: Union[str, Sequence[str], None] = "4b7e2a91c6d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("medicos", sa.Column("private_key_cipher_version", sa.String(64), nullable=True))
    op.execute(
        "UPDATE medicos SET private_key_cipher_version = 'FERNET_HKDF_SHA256_V1' "
        "WHERE private_key_enc IS NOT NULL"
    )

    op.add_column("historial_llaves_fea", sa.Column("key_id", sa.String(64), nullable=True))
    op.add_column(
        "historial_llaves_fea",
        sa.Column("estado", sa.String(32), nullable=False, server_default="ACTIVA"),
    )
    op.execute("UPDATE historial_llaves_fea SET key_id = 'legacy-' || id::text")
    op.execute(
        "UPDATE historial_llaves_fea SET estado = CASE WHEN activo THEN 'ACTIVA' ELSE 'INACTIVA' END"
    )
    op.alter_column("historial_llaves_fea", "key_id", nullable=False)
    op.create_index(
        op.f("ix_historial_llaves_fea_key_id"),
        "historial_llaves_fea",
        ["key_id"],
        unique=True,
    )
    op.create_index(
        "uq_historial_llaves_fea_unica_activa",
        "historial_llaves_fea",
        ["medico_id"],
        unique=True,
        postgresql_where=sa.text("activo IS TRUE"),
    )

    op.add_column("firmas_documentos_clinicos", sa.Column("key_id", sa.String(64), nullable=True))
    op.add_column(
        "firmas_documentos_clinicos",
        sa.Column("signature_schema_version", sa.String(32), nullable=False, server_default="LEGACY_V1"),
    )
    op.add_column("firmas_documentos_clinicos", sa.Column("canonical_payload", sa.Text(), nullable=True))
    op.add_column("firmas_documentos_clinicos", sa.Column("payload_hash", sa.String(64), nullable=True))
    op.add_column("firmas_documentos_clinicos", sa.Column("document_version", sa.String(128), nullable=True))
    op.add_column("firmas_documentos_clinicos", sa.Column("pdf_hash", sa.String(64), nullable=True))
    op.add_column("firmas_documentos_clinicos", sa.Column("pdf_identifier", sa.String(255), nullable=True))
    op.add_column(
        "firmas_documentos_clinicos",
        sa.Column("tsa_status", sa.String(32), nullable=False, server_default="SIN_TSA"),
    )
    op.add_column("firmas_documentos_clinicos", sa.Column("tsa_nonce", sa.String(128), nullable=True))
    op.add_column(
        "firmas_documentos_clinicos",
        sa.Column("tsa_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("firmas_documentos_clinicos", sa.Column("tsa_last_error", sa.Text(), nullable=True))
    op.add_column("firmas_documentos_clinicos", sa.Column("tsa_verified_at", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE firmas_documentos_clinicos SET tsa_status = "
        "CASE WHEN tsa_token IS NULL THEN 'SIN_TSA' ELSE 'TSA_LEGACY_NO_VERIFICADO' END"
    )
    op.create_index(
        op.f("ix_firmas_documentos_clinicos_key_id"),
        "firmas_documentos_clinicos",
        ["key_id"],
    )
    op.create_index(
        op.f("ix_firmas_documentos_clinicos_signature_schema_version"),
        "firmas_documentos_clinicos",
        ["signature_schema_version"],
    )
    op.create_index(
        op.f("ix_firmas_documentos_clinicos_tsa_status"),
        "firmas_documentos_clinicos",
        ["tsa_status"],
    )
    op.create_foreign_key(
        "fk_firmas_documentos_key_id",
        "firmas_documentos_clinicos",
        "historial_llaves_fea",
        ["key_id"],
        ["key_id"],
    )

    # Public key history is append-only. The sole permitted update is the
    # one-way ACTIVA -> INACTIVA transition used by explicit rotation.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_historial_llaves_fea()
        RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'historial_llaves_fea es append-only';
          END IF;
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.key_id IS DISTINCT FROM OLD.key_id
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
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_protect_historial_llaves_fea
        BEFORE UPDATE OR DELETE ON historial_llaves_fea
        FOR EACH ROW EXECUTE FUNCTION protect_historial_llaves_fea();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_protect_historial_llaves_fea ON historial_llaves_fea")
    op.execute("DROP FUNCTION IF EXISTS protect_historial_llaves_fea()")
    op.drop_constraint("fk_firmas_documentos_key_id", "firmas_documentos_clinicos", type_="foreignkey")
    op.drop_index(op.f("ix_firmas_documentos_clinicos_tsa_status"), table_name="firmas_documentos_clinicos")
    op.drop_index(op.f("ix_firmas_documentos_clinicos_signature_schema_version"), table_name="firmas_documentos_clinicos")
    op.drop_index(op.f("ix_firmas_documentos_clinicos_key_id"), table_name="firmas_documentos_clinicos")
    for column in (
        "tsa_verified_at",
        "tsa_last_error",
        "tsa_attempts",
        "tsa_nonce",
        "tsa_status",
        "pdf_identifier",
        "pdf_hash",
        "document_version",
        "payload_hash",
        "canonical_payload",
        "signature_schema_version",
        "key_id",
    ):
        op.drop_column("firmas_documentos_clinicos", column)
    op.drop_index("uq_historial_llaves_fea_unica_activa", table_name="historial_llaves_fea")
    op.drop_index(op.f("ix_historial_llaves_fea_key_id"), table_name="historial_llaves_fea")
    op.drop_column("historial_llaves_fea", "estado")
    op.drop_column("historial_llaves_fea", "key_id")
    op.drop_column("medicos", "private_key_cipher_version")
