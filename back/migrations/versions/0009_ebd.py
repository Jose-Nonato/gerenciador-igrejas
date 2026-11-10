"""Fase 5: Escola Bíblica Dominical (classes, professores, alunos, aulas e presença).

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _igreja_fk() -> sa.Column:
    return sa.Column(
        "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
    )


def _fk(coluna: str, tabela: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        coluna, sa.Uuid(), sa.ForeignKey(f"{tabela}.id", ondelete="RESTRICT"), nullable=nullable
    )


def upgrade() -> None:
    op.create_table(
        "ebd_classe",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("faixa_etaria", sa.String(100)),
        sa.Column("ativa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("igreja_id", "nome", name="uq_ebd_classe_igreja_nome"),
    )
    op.create_index("ix_ebd_classe_igreja_id", "ebd_classe", ["igreja_id"])

    op.create_table(
        "ebd_professor",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        _fk("classe_id", "ebd_classe"),
        _fk("membro_id", "membro"),
        sa.Column("inicio", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("fim", sa.Date()),
        sa.CheckConstraint("fim IS NULL OR fim >= inicio", name="ebd_professor_periodo"),
    )
    op.create_index("ix_ebd_professor_igreja_id", "ebd_professor", ["igreja_id"])
    op.create_index("ix_ebd_professor_classe_id", "ebd_professor", ["classe_id"])
    op.create_index("ix_ebd_professor_membro_id", "ebd_professor", ["membro_id"])
    op.create_index(
        "uq_ebd_professor_ativo",
        "ebd_professor",
        ["classe_id", "membro_id"],
        unique=True,
        postgresql_where=sa.text("fim IS NULL"),
    )

    op.create_table(
        "ebd_aluno",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        _fk("classe_id", "ebd_classe"),
        _fk("membro_id", "membro", nullable=True),
        sa.Column("nome_externo", sa.String(255)),
        sa.Column("entrou_em", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("saiu_em", sa.Date()),
        sa.CheckConstraint(
            "(membro_id IS NULL AND nome_externo IS NOT NULL)"
            " OR (membro_id IS NOT NULL AND nome_externo IS NULL)",
            name="ebd_aluno_identificacao",
        ),
    )
    op.create_index("ix_ebd_aluno_igreja_id", "ebd_aluno", ["igreja_id"])
    op.create_index("ix_ebd_aluno_classe_id", "ebd_aluno", ["classe_id"])
    op.create_index("ix_ebd_aluno_membro_id", "ebd_aluno", ["membro_id"])
    op.create_index(
        "uq_ebd_aluno_ativo",
        "ebd_aluno",
        ["classe_id", "membro_id"],
        unique=True,
        postgresql_where=sa.text("saiu_em IS NULL AND membro_id IS NOT NULL"),
    )

    op.create_table(
        "ebd_aula",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        _fk("classe_id", "ebd_classe"),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("licao", sa.String(255)),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("classe_id", "data", name="uq_ebd_aula_classe_data"),
    )
    op.create_index("ix_ebd_aula_igreja_id", "ebd_aula", ["igreja_id"])
    op.create_index("ix_ebd_aula_classe_id", "ebd_aula", ["classe_id"])

    op.create_table(
        "ebd_presenca",
        _igreja_fk(),
        _fk("aula_id", "ebd_aula"),
        _fk("aluno_id", "ebd_aluno"),
        sa.Column("status", sa.String(1), nullable=False),
        sa.PrimaryKeyConstraint("aula_id", "aluno_id", name="pk_ebd_presenca"),
        sa.CheckConstraint("status IN ('P', 'A', 'J')", name="statuspresenca"),
    )
    op.create_index("ix_ebd_presenca_igreja_id", "ebd_presenca", ["igreja_id"])
    op.create_index("ix_ebd_presenca_aluno_id", "ebd_presenca", ["aluno_id"])


def downgrade() -> None:
    op.drop_table("ebd_presenca")
    op.drop_table("ebd_aula")
    op.drop_table("ebd_aluno")
    op.drop_table("ebd_professor")
    op.drop_table("ebd_classe")
