"""Agendamento de conversas com pastor e presbíteros (disponibilidade e atendimentos).

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _igreja_fk() -> sa.Column:
    return sa.Column(
        "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
    )


def _fk(coluna: str, tabela: str) -> sa.Column:
    return sa.Column(
        coluna, sa.Uuid(), sa.ForeignKey(f"{tabela}.id", ondelete="RESTRICT"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "disponibilidade_atendimento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        _fk("oficial_id", "usuario"),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fim", sa.Time(), nullable=False),
        sa.Column("duracao_min", sa.SmallInteger(), nullable=False),
        sa.Column("modalidade", sa.String(10), nullable=False),
        sa.Column("local", sa.String(255)),
        sa.Column("ativa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("dia_semana BETWEEN 0 AND 6", name="disponibilidade_dia_semana"),
        sa.CheckConstraint("hora_fim > hora_inicio", name="disponibilidade_horario"),
        sa.CheckConstraint("duracao_min > 0", name="disponibilidade_duracao"),
        sa.CheckConstraint(
            "modalidade IN ('presencial', 'online', 'visita')",
            name="modalidadeatendimento",
        ),
    )
    op.create_index(
        "ix_disponibilidade_atendimento_igreja_id", "disponibilidade_atendimento", ["igreja_id"]
    )
    op.create_index(
        "ix_disponibilidade_atendimento_oficial_id", "disponibilidade_atendimento", ["oficial_id"]
    )

    op.create_table(
        "atendimento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        _fk("solicitante_id", "membro"),
        _fk("oficial_id", "usuario"),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modalidade", sa.String(10), nullable=False),
        sa.Column("local", sa.String(255)),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("categoria", sa.String(21), nullable=False),
        sa.Column("assunto", sa.Text()),
        sa.Column("justificativa", sa.String(500)),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("fim > inicio", name="atendimento_periodo"),
        sa.CheckConstraint(
            "modalidade IN ('presencial', 'online', 'visita')",
            name="modalidadeatendimento",
        ),
        sa.CheckConstraint(
            "status IN ('solicitado', 'confirmado', 'recusado', 'cancelado', 'realizado', 'faltou')",
            name="statusatendimento",
        ),
        sa.CheckConstraint(
            "categoria IN ('aconselhamento', 'orientacao_espiritual', 'familiar', 'visita', 'outro')",
            name="categoriaatendimento",
        ),
    )
    op.create_index("ix_atendimento_igreja_id", "atendimento", ["igreja_id"])
    op.create_index("ix_atendimento_solicitante_id", "atendimento", ["solicitante_id"])
    op.create_index("ix_atendimento_oficial_id", "atendimento", ["oficial_id"])
    op.create_index(
        "uq_atendimento_horario_ativo",
        "atendimento",
        ["oficial_id", "inicio"],
        unique=True,
        postgresql_where=sa.text("status IN ('solicitado', 'confirmado')"),
    )


def downgrade() -> None:
    op.drop_table("atendimento")
    op.drop_table("disponibilidade_atendimento")
