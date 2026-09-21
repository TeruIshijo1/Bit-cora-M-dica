"""Repair AF-02 schema drift in legacy installations.

Revision ID: 9e2c4b6d8f10
Revises: f7a9c2d4e6b1
Create Date: 2026-09-18 09:25:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9e2c4b6d8f10"
down_revision: Union[str, Sequence[str], None] = "f7a9c2d4e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _repair_template_metadata(connection, table_name: str, *, medical: bool) -> None:
    inspector = sa.inspect(connection)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    status_added = "biometric_status" not in columns
    additions = (
        ("biometric_status", sa.Column("biometric_status", sa.String(32), nullable=False, server_default="SIN_BIOMETRIA")),
        ("template_format", sa.Column("template_format", sa.String(32), nullable=True)),
        ("template_version", sa.Column("template_version", sa.Integer(), nullable=True)),
        ("fecha_enrolamiento", sa.Column("fecha_enrolamiento", sa.DateTime(), nullable=True)),
        ("requiere_reenrolamiento", sa.Column("requiere_reenrolamiento", sa.Boolean(), nullable=False, server_default=sa.false())),
    )
    for name, column in additions:
        if name not in columns:
            op.add_column(table_name, column)
    if medical and "requiere_actualizacion_fea" not in columns:
        op.add_column(
            table_name,
            sa.Column("requiere_actualizacion_fea", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    index_name = f"ix_{table_name}_biometric_status"
    indexes = {index["name"] for index in sa.inspect(connection).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, ["biometric_status"])
    if status_added:
        op.execute(sa.text(
            f"UPDATE {table_name} "
            "SET biometric_status = CASE "
            "WHEN fmd_template IS NULL OR btrim(fmd_template) = '' THEN 'SIN_BIOMETRIA' "
            "ELSE 'LEGACY_RAW' END, "
            "requiere_reenrolamiento = CASE "
            "WHEN fmd_template IS NULL OR btrim(fmd_template) = '' THEN FALSE ELSE TRUE END"
        ))


def upgrade() -> None:
    """Converge databases stamped at head before all AF-02 fields existed."""
    connection = op.get_bind()
    _repair_template_metadata(connection, "medicos", medical=True)
    _repair_template_metadata(connection, "biometria_firmantes_episodio", medical=False)

    medicos_columns = {
        column["name"] for column in sa.inspect(connection).get_columns("medicos")
    }
    if "private_key_cipher_version" not in medicos_columns:
        op.add_column("medicos", sa.Column("private_key_cipher_version", sa.String(64), nullable=True))
        op.execute(
            "UPDATE medicos SET private_key_cipher_version = 'FERNET_HKDF_SHA256_V1' "
            "WHERE private_key_enc IS NOT NULL"
        )
    if "biometric_reenrolled_by_id" not in medicos_columns:
        op.add_column("medicos", sa.Column("biometric_reenrolled_by_id", sa.Integer(), nullable=True))
    if "biometric_reenrolled_at" not in medicos_columns:
        op.add_column("medicos", sa.Column("biometric_reenrolled_at", sa.DateTime(), nullable=True))
    foreign_keys = {
        foreign_key.get("name") for foreign_key in sa.inspect(connection).get_foreign_keys("medicos")
    }
    if "fk_medicos_biometric_reenrolled_by" not in foreign_keys:
        op.create_foreign_key(
            "fk_medicos_biometric_reenrolled_by",
            "medicos",
            "usuarios",
            ["biometric_reenrolled_by_id"],
            ["id"],
        )

    inspector = sa.inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("biometric_challenges")}

    if "expected_identity_ref" not in columns:
        op.add_column(
            "biometric_challenges",
            sa.Column("expected_identity_ref", sa.String(length=128), nullable=True),
        )
    if "acquisition_id" not in columns:
        op.add_column(
            "biometric_challenges",
            sa.Column("acquisition_id", sa.String(length=128), nullable=True),
        )

    indexes = {
        index["name"] for index in sa.inspect(connection).get_indexes("biometric_challenges")
    }
    if "ix_biometric_challenges_expected_identity_ref" not in indexes:
        op.create_index(
            "ix_biometric_challenges_expected_identity_ref",
            "biometric_challenges",
            ["expected_identity_ref"],
        )
    if "ix_biometric_challenges_acquisition_id" not in indexes:
        op.create_index(
            "ix_biometric_challenges_acquisition_id",
            "biometric_challenges",
            ["acquisition_id"],
            unique=True,
        )


def downgrade() -> None:
    # These fields belong to earlier AF-02/AF-01..11 revisions. The repair only
    # converges drifted installations, so downgrading it must preserve the data.
    pass
