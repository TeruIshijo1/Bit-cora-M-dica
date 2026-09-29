"""Add per-user Banco de Sangre biometrics and document signer binding.

Revision ID: a8c1d3e5f709
Revises: b2d4f6a8c0e1
Create Date: 2026-09-28 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8c1d3e5f709"
down_revision: Union[str, Sequence[str], None] = "b2d4f6a8c0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("fmd_template", sa.Text(), nullable=True))
    op.add_column(
        "usuarios",
        sa.Column("biometric_status", sa.String(length=32), nullable=False, server_default="SIN_BIOMETRIA"),
    )
    op.add_column("usuarios", sa.Column("template_format", sa.String(length=32), nullable=True))
    op.add_column("usuarios", sa.Column("template_version", sa.Integer(), nullable=True))
    op.add_column("usuarios", sa.Column("fecha_enrolamiento", sa.DateTime(), nullable=True))
    op.add_column("usuarios", sa.Column("biometric_updated_by_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_usuarios_biometric_updated_by",
        "usuarios",
        "usuarios",
        ["biometric_updated_by_id"],
        ["id"],
    )
    op.create_index("ix_usuarios_biometric_status", "usuarios", ["biometric_status"])

    op.add_column(
        "firmas_documentos_clinicos",
        sa.Column("usuario_firmante_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_firmas_usuario_firmante",
        "firmas_documentos_clinicos",
        "usuarios",
        ["usuario_firmante_id"],
        ["id"],
    )

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
                   OR NEW.usuario_firmante_id IS DISTINCT FROM OLD.usuario_firmante_id
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


def downgrade() -> None:
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
    op.drop_constraint("fk_firmas_usuario_firmante", "firmas_documentos_clinicos", type_="foreignkey")
    op.drop_column("firmas_documentos_clinicos", "usuario_firmante_id")
    op.drop_index("ix_usuarios_biometric_status", table_name="usuarios")
    op.drop_constraint("fk_usuarios_biometric_updated_by", "usuarios", type_="foreignkey")
    op.drop_column("usuarios", "biometric_updated_by_id")
    op.drop_column("usuarios", "fecha_enrolamiento")
    op.drop_column("usuarios", "template_version")
    op.drop_column("usuarios", "template_format")
    op.drop_column("usuarios", "biometric_status")
    op.drop_column("usuarios", "fmd_template")
