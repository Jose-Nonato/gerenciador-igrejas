"""Fase 3b: liderança (diretoria) das sociedades.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

CARGOS = ("presidente", "vice_presidente", "secretario", "tesoureiro", "conselheiro", "outro")
# Cargos com um único ocupante em exercício (ver models.enums.CARGOS_UNICOS)
CARGOS_UNICOS = ("presidente", "secretario", "tesoureiro", "vice_presidente")


def _in(coluna: str, valores: tuple[str, ...]) -> str:
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


def upgrade() -> None:
    op.create_table(
        "lideranca",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "sociedade_id",
            sa.Uuid(),
            sa.ForeignKey("sociedade.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "membro_id", sa.Uuid(), sa.ForeignKey("membro.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("cargo", sa.String(15), nullable=False),
        sa.Column("cargo_descricao", sa.String(100)),
        sa.Column("inicio", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("fim", sa.Date()),
        sa.CheckConstraint(_in("cargo", CARGOS), name="cargolideranca"),
        sa.CheckConstraint(
            "(cargo = 'outro' AND cargo_descricao IS NOT NULL)"
            " OR (cargo <> 'outro' AND cargo_descricao IS NULL)",
            name="lideranca_descricao",
        ),
        sa.CheckConstraint("fim IS NULL OR fim >= inicio", name="lideranca_periodo"),
    )
    op.create_index("ix_lideranca_igreja_id", "lideranca", ["igreja_id"])
    op.create_index("ix_lideranca_sociedade_id", "lideranca", ["sociedade_id"])
    op.create_index("ix_lideranca_membro_id", "lideranca", ["membro_id"])
    op.create_index(
        "uq_lideranca_cargo_unico_ativo",
        "lideranca",
        ["sociedade_id", "cargo"],
        unique=True,
        postgresql_where=sa.text(f"fim IS NULL AND cargo IN ({', '.join(repr(c) for c in CARGOS_UNICOS)})"),
    )


def downgrade() -> None:
    op.drop_table("lideranca")
