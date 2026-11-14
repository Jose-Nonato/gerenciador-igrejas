"""Agenda, fase 3: bloqueios de agenda e remarcação proposta pelo oficial.

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_STATUS_ANTIGOS = "'solicitado', 'confirmado', 'recusado', 'cancelado', 'realizado', 'faltou'"
_STATUS_NOVOS = _STATUS_ANTIGOS + ", 'remarcacao'"


def upgrade() -> None:
    # Novo status `remarcacao`: o CHECK do banco precisa aceitá-lo
    op.drop_constraint("statusatendimento", "atendimento", type_="check")
    op.create_check_constraint("statusatendimento", "atendimento", f"status IN ({_STATUS_NOVOS})")

    op.add_column("atendimento", sa.Column("proposta_inicio", sa.DateTime(timezone=True)))
    op.add_column("atendimento", sa.Column("proposta_fim", sa.DateTime(timezone=True)))
    op.add_column("atendimento", sa.Column("proposta_modalidade", sa.String(10)))
    op.add_column("atendimento", sa.Column("proposta_local", sa.String(255)))
    op.create_check_constraint(
        "atendimento_proposta",
        "atendimento",
        "(proposta_inicio IS NULL) = (proposta_fim IS NULL)",
    )
    op.create_check_constraint(
        "atendimento_proposta_modalidade",
        "atendimento",
        "proposta_modalidade IS NULL OR proposta_modalidade IN ('presencial', 'online', 'visita')",
    )

    op.create_table(
        "bloqueio_agenda",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "oficial_id", sa.Uuid(), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("de", sa.Date(), nullable=False),
        sa.Column("ate", sa.Date(), nullable=False),
        sa.Column("motivo", sa.String(200)),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("ate >= de", name="bloqueio_agenda_periodo"),
    )
    op.create_index("ix_bloqueio_agenda_igreja_id", "bloqueio_agenda", ["igreja_id"])
    op.create_index("ix_bloqueio_agenda_oficial_id", "bloqueio_agenda", ["oficial_id"])


def downgrade() -> None:
    op.drop_table("bloqueio_agenda")
    op.drop_constraint("atendimento_proposta_modalidade", "atendimento", type_="check")
    op.drop_constraint("atendimento_proposta", "atendimento", type_="check")
    op.drop_column("atendimento", "proposta_local")
    op.drop_column("atendimento", "proposta_modalidade")
    op.drop_column("atendimento", "proposta_fim")
    op.drop_column("atendimento", "proposta_inicio")
    # Sem o status `remarcacao`: uma remarcação ainda sem resposta vira cancelamento
    op.execute("UPDATE atendimento SET status = 'cancelado' WHERE status = 'remarcacao'")
    op.drop_constraint("statusatendimento", "atendimento", type_="check")
    op.create_check_constraint("statusatendimento", "atendimento", f"status IN ({_STATUS_ANTIGOS})")
