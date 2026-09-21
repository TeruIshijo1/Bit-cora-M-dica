"""preproduction security, durable audit and token revocation

Revision ID: d4f5a6b7c8d9
Revises: 8f3c2d1a7b90
Create Date: 2026-09-17 23:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "8f3c2d1a7b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("auditoria_logs", sa.Column("request_id", sa.String(128), nullable=True))
    op.add_column("auditoria_logs", sa.Column("operation_id", sa.String(128), nullable=True))
    op.add_column("auditoria_logs", sa.Column("actor_real", sa.String(255), nullable=True))
    op.add_column("auditoria_logs", sa.Column("actor_effective", sa.String(255), nullable=True))
    op.add_column("auditoria_logs", sa.Column("motivo_impersonacion", sa.String(500), nullable=True))
    op.add_column("auditoria_logs", sa.Column("resultado", sa.String(32), nullable=True))
    op.execute("""
        UPDATE auditoria_logs
           SET request_id = COALESCE(request_id, 'legacy-' || id::text),
               actor_real = COALESCE(actor_real, CASE WHEN usuario_id IS NULL THEN 'sistema' ELSE 'usuario:' || usuario_id::text END),
               actor_effective = COALESCE(actor_effective, CASE WHEN usuario_id IS NULL THEN 'sistema' ELSE 'usuario:' || usuario_id::text END),
               resultado = COALESCE(resultado, 'LEGACY')
    """)
    op.alter_column("auditoria_logs", "request_id", nullable=False)
    op.alter_column("auditoria_logs", "actor_real", nullable=False)
    op.alter_column("auditoria_logs", "actor_effective", nullable=False)
    op.alter_column("auditoria_logs", "resultado", nullable=False)
    op.alter_column("auditoria_logs", "accion", nullable=False)
    op.create_index("ix_auditoria_logs_request_id", "auditoria_logs", ["request_id"])
    op.create_index("ix_auditoria_logs_operation_id", "auditoria_logs", ["operation_id"])

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(64), primary_key=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("reason", sa.String(255), nullable=False, server_default="LOGOUT"),
        sa.Column("revoked_by", sa.String(255), nullable=True),
    )
    op.create_index("ix_revoked_tokens_subject", "revoked_tokens", ["subject"])
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])

    op.execute("""
        CREATE OR REPLACE FUNCTION hes_block_auditoria_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'auditoria_logs es append-only';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_auditoria_logs_append_only
        BEFORE UPDATE OR DELETE ON auditoria_logs
        FOR EACH ROW EXECUTE FUNCTION hes_block_auditoria_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_auditoria_logs_append_only ON auditoria_logs")
    op.execute("DROP FUNCTION IF EXISTS hes_block_auditoria_mutation()")
    op.drop_table("revoked_tokens")
    op.drop_column("usuarios", "must_change_password")
    op.drop_index("ix_auditoria_logs_operation_id", table_name="auditoria_logs")
    op.drop_index("ix_auditoria_logs_request_id", table_name="auditoria_logs")
    for column in ("resultado", "motivo_impersonacion", "actor_effective", "actor_real", "operation_id", "request_id"):
        op.drop_column("auditoria_logs", column)
