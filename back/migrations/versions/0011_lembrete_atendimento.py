"""Lembrete de atendimento: marca quando o lembrete por e-mail já foi enviado.

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("atendimento", sa.Column("lembrete_enviado_em", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("atendimento", "lembrete_enviado_em")
