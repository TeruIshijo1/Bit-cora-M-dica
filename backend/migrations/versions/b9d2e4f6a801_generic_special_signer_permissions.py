"""Allow enrolled user accounts to sign configured special areas by format.

Revision ID: b9d2e4f6a801
Revises: a8c1d3e5f709
Create Date: 2026-09-29 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9d2e4f6a801"
down_revision: Union[str, Sequence[str], None] = "a8c1d3e5f709"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("formatos_firma_permitidos", sa.Text(), nullable=True, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "formatos_firma_permitidos")
