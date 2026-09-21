"""durable clinical synchronization operations and idempotency

Revision ID: 8f3c2d1a7b90
Revises: c31f4a7d9e20
Create Date: 2026-09-17 22:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8f3c2d1a7b90"
down_revision: Union[str, Sequence[str], None] = "c31f4a7d9e20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinical_sync_operations",
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("operation_type", sa.String(80), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", sa.String(255), nullable=False),
        sa.Column("patient_ref", sa.String(80), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("local_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('PENDING','PROCESSING','SYNCED','RETRYABLE_ERROR','FAILED','REQUIRES_RECONCILIATION')",
            name="ck_clinical_sync_operation_state",
        ),
        sa.PrimaryKeyConstraint("operation_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_clinical_sync_idempotency_key"),
    )
    op.create_index(
        "ix_clinical_sync_operations_operation_type",
        "clinical_sync_operations",
        ["operation_type"],
    )
    op.create_index(
        "ix_clinical_sync_operations_aggregate_id",
        "clinical_sync_operations",
        ["aggregate_id"],
    )
    op.create_index(
        "ix_clinical_sync_operations_patient_ref",
        "clinical_sync_operations",
        ["patient_ref"],
    )
    op.create_index(
        "ix_clinical_sync_operations_state",
        "clinical_sync_operations",
        ["state"],
    )
    op.create_index(
        "ix_clinical_sync_operations_next_attempt_at",
        "clinical_sync_operations",
        ["next_attempt_at"],
    )
    op.create_index(
        "idx_clinical_sync_reconciliation",
        "clinical_sync_operations",
        ["state", "next_attempt_at", "created_at"],
    )

    op.create_table(
        "clinical_sync_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("error_class", sa.String(120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["clinical_sync_operations.operation_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "operation_id",
            "attempt_number",
            name="uq_clinical_sync_attempt_number",
        ),
    )
    op.create_index(
        "ix_clinical_sync_attempts_operation_id",
        "clinical_sync_attempts",
        ["operation_id"],
    )

    for table_name in (
        "firmas_documentos_clinicos",
        "historico_notas_clinicas",
        "dieta_cuidados_prescripciones",
    ):
        op.add_column(
            table_name,
            sa.Column("clinical_sync_operation_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table_name}_clinical_sync_operation",
            table_name,
            "clinical_sync_operations",
            ["clinical_sync_operation_id"],
            ["operation_id"],
        )
        op.create_index(
            f"ix_{table_name}_clinical_sync_operation_id",
            table_name,
            ["clinical_sync_operation_id"],
            unique=True,
        )


def downgrade() -> None:
    for table_name in (
        "dieta_cuidados_prescripciones",
        "historico_notas_clinicas",
        "firmas_documentos_clinicos",
    ):
        op.drop_index(
            f"ix_{table_name}_clinical_sync_operation_id",
            table_name=table_name,
        )
        op.drop_constraint(
            f"fk_{table_name}_clinical_sync_operation",
            table_name,
            type_="foreignkey",
        )
        op.drop_column(table_name, "clinical_sync_operation_id")

    op.drop_index("ix_clinical_sync_attempts_operation_id", table_name="clinical_sync_attempts")
    op.drop_table("clinical_sync_attempts")
    op.drop_index("idx_clinical_sync_reconciliation", table_name="clinical_sync_operations")
    op.drop_index("ix_clinical_sync_operations_next_attempt_at", table_name="clinical_sync_operations")
    op.drop_index("ix_clinical_sync_operations_state", table_name="clinical_sync_operations")
    op.drop_index("ix_clinical_sync_operations_patient_ref", table_name="clinical_sync_operations")
    op.drop_index("ix_clinical_sync_operations_aggregate_id", table_name="clinical_sync_operations")
    op.drop_index("ix_clinical_sync_operations_operation_type", table_name="clinical_sync_operations")
    op.drop_table("clinical_sync_operations")
