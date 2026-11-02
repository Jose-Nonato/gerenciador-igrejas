"""Fase 3: sociedades internas, sócios, reuniões e presença.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SIGLA = ("UCP", "UPA", "UMP", "SAF", "UPH")
TIPO_SOCIO = ("ativo", "cooperador", "nao_membro")
STATUS_PRESENCA = ("P", "A", "J")


def _in(coluna: str, valores: tuple[str, ...]) -> str:
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


def _igreja_fk() -> sa.Column:
    return sa.Column(
        "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "sociedade",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        sa.Column("sigla", sa.String(3), nullable=False),
        sa.Column("nome", sa.String(255)),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("igreja_id", "sigla", name="uq_sociedade_igreja_sigla"),
        sa.CheckConstraint(_in("sigla", SIGLA), name="siglasociedade"),
    )
    op.create_index("ix_sociedade_igreja_id", "sociedade", ["igreja_id"])

    op.create_table(
        "socio",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        sa.Column(
            "sociedade_id",
            sa.Uuid(),
            sa.ForeignKey("sociedade.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("membro_id", sa.Uuid(), sa.ForeignKey("membro.id", ondelete="RESTRICT")),
        sa.Column("nome_externo", sa.String(255)),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("entrou_em", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("saiu_em", sa.Date()),
        sa.CheckConstraint(_in("tipo", TIPO_SOCIO), name="tiposocio"),
        sa.CheckConstraint(
            "(tipo = 'nao_membro' AND membro_id IS NULL AND nome_externo IS NOT NULL)"
            " OR (tipo <> 'nao_membro' AND membro_id IS NOT NULL AND nome_externo IS NULL)",
            name="socio_identificacao",
        ),
    )
    op.create_index("ix_socio_igreja_id", "socio", ["igreja_id"])
    op.create_index("ix_socio_sociedade_id", "socio", ["sociedade_id"])
    op.create_index("ix_socio_membro_id", "socio", ["membro_id"])
    op.create_index(
        "uq_socio_sociedade_membro_ativo",
        "socio",
        ["sociedade_id", "membro_id"],
        unique=True,
        postgresql_where=sa.text("saiu_em IS NULL AND membro_id IS NOT NULL"),
    )

    op.create_table(
        "reuniao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        sa.Column(
            "sociedade_id",
            sa.Uuid(),
            sa.ForeignKey("sociedade.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("tema", sa.String(255)),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("sociedade_id", "data", name="uq_reuniao_sociedade_data"),
    )
    op.create_index("ix_reuniao_igreja_id", "reuniao", ["igreja_id"])
    op.create_index("ix_reuniao_sociedade_id", "reuniao", ["sociedade_id"])

    op.create_table(
        "presenca",
        _igreja_fk(),
        sa.Column(
            "reuniao_id", sa.Uuid(), sa.ForeignKey("reuniao.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "socio_id", sa.Uuid(), sa.ForeignKey("socio.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("status", sa.String(1), nullable=False),
        sa.PrimaryKeyConstraint("reuniao_id", "socio_id", name="pk_presenca"),
        sa.CheckConstraint(_in("status", STATUS_PRESENCA), name="statuspresenca"),
    )
    op.create_index("ix_presenca_igreja_id", "presenca", ["igreja_id"])
    op.create_index("ix_presenca_socio_id", "presenca", ["socio_id"])


def downgrade() -> None:
    op.drop_table("presenca")
    op.drop_table("reuniao")
    op.drop_table("socio")
    op.drop_table("sociedade")
