"""biometric security stabilization

Revision ID: 4b7e2a91c6d0
Revises: 9024a9c93603
Create Date: 2026-09-17 18:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b7e2a91c6d0"
down_revision: Union[str, Sequence[str], None] = "9024a9c93603"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_biometric_columns(table_name: str, *, medical: bool = False) -> None:
    op.add_column(
        table_name,
        sa.Column("biometric_status", sa.String(length=32), nullable=False, server_default="SIN_BIOMETRIA"),
    )
    op.add_column(table_name, sa.Column("template_format", sa.String(length=32), nullable=True))
    op.add_column(table_name, sa.Column("template_version", sa.Integer(), nullable=True))
    op.add_column(table_name, sa.Column("fecha_enrolamiento", sa.DateTime(), nullable=True))
    op.add_column(
        table_name,
        sa.Column("requiere_reenrolamiento", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    if medical:
        op.add_column(
            table_name,
            sa.Column("requiere_actualizacion_fea", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    op.create_index(op.f(f"ix_{table_name}_biometric_status"), table_name, ["biometric_status"])


def upgrade() -> None:
    op.alter_column(
        "medicos",
        "fmd_template",
        existing_type=sa.String(),
        type_=sa.Text(),
        existing_nullable=True,
    )
    _add_biometric_columns("medicos", medical=True)
    _add_biometric_columns("biometria_firmantes_episodio")

    # No se transforma ni elimina material histórico. Cualquier valor preexistente
    # queda bloqueado como LEGACY_RAW hasta un reenrolamiento explícito.
    op.execute(
        """
        UPDATE medicos
           SET biometric_status = CASE
                   WHEN fmd_template IS NULL OR btrim(fmd_template) = '' THEN 'SIN_BIOMETRIA'
                   ELSE 'LEGACY_RAW'
               END,
               requiere_reenrolamiento = CASE
                   WHEN fmd_template IS NULL OR btrim(fmd_template) = '' THEN FALSE
                   ELSE TRUE
               END
        """
    )
    op.execute(
        """
        UPDATE biometria_firmantes_episodio
           SET biometric_status = CASE
                   WHEN fmd_template IS NULL OR btrim(fmd_template) = '' THEN 'SIN_BIOMETRIA'
                   ELSE 'LEGACY_RAW'
               END,
               requiere_reenrolamiento = CASE
                   WHEN fmd_template IS NULL OR btrim(fmd_template) = '' THEN FALSE
                   ELSE TRUE
               END
        """
    )

    op.create_table(
        "biometric_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("subject_ref", sa.String(length=128), nullable=True),
        sa.Column("expected_identity_ref", sa.String(length=128), nullable=True),
        sa.Column("patient_ref", sa.String(length=128), nullable=True),
        sa.Column("document_code", sa.String(length=128), nullable=True),
        sa.Column("document_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    for column in (
        "id",
        "action",
        "session_id",
        "subject_ref",
        "expected_identity_ref",
        "patient_ref",
        "expires_at",
        "consumed_at",
    ):
        op.create_index(op.f(f"ix_biometric_challenges_{column}"), "biometric_challenges", [column])


def downgrade() -> None:
    for column in (
        "consumed_at",
        "expires_at",
        "patient_ref",
        "subject_ref",
        "expected_identity_ref",
        "session_id",
        "action",
        "id",
    ):
        op.drop_index(op.f(f"ix_biometric_challenges_{column}"), table_name="biometric_challenges")
    op.drop_table("biometric_challenges")

    op.alter_column(
        "medicos",
        "fmd_template",
        existing_type=sa.Text(),
        type_=sa.String(),
        existing_nullable=True,
    )

    op.drop_index(op.f("ix_biometria_firmantes_episodio_biometric_status"), table_name="biometria_firmantes_episodio")
    for column in (
        "requiere_reenrolamiento",
        "fecha_enrolamiento",
        "template_version",
        "template_format",
        "biometric_status",
    ):
        op.drop_column("biometria_firmantes_episodio", column)

    op.drop_index(op.f("ix_medicos_biometric_status"), table_name="medicos")
    for column in (
        "requiere_actualizacion_fea",
        "requiere_reenrolamiento",
        "fecha_enrolamiento",
        "template_version",
        "template_format",
        "biometric_status",
    ):
        op.drop_column("medicos", column)
