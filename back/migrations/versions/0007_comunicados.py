"""Fase 4: comunicados (mural da igreja).

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

CATEGORIA = ("aviso", "evento", "pastoral", "oracao")
STATUS = ("rascunho", "agendado", "publicado")
PUBLICO = ("igreja", "comungantes", "oficiais", "sociedade", "professores_ebd")


def _in(coluna: str, valores: tuple[str, ...]) -> str:
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


def upgrade() -> None:
    op.create_table(
        "comunicado",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("categoria", sa.String(8), nullable=False),
        sa.Column("publico", sa.String(15), nullable=False),
        sa.Column("sociedade_id", sa.Uuid(), sa.ForeignKey("sociedade.id", ondelete="RESTRICT")),
        sa.Column("status", sa.String(9), nullable=False),
        sa.Column("publicar_em", sa.DateTime(timezone=True)),
        sa.Column("publicado_em", sa.DateTime(timezone=True)),
        sa.Column("autor_id", sa.Uuid(), sa.ForeignKey("usuario.id", ondelete="SET NULL")),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("excluido_em", sa.DateTime(timezone=True)),
        sa.CheckConstraint(_in("categoria", CATEGORIA), name="categoriapost"),
        sa.CheckConstraint(_in("publico", PUBLICO), name="tipopublico"),
        sa.CheckConstraint(_in("status", STATUS), name="statuspost"),
        sa.CheckConstraint(
            "(publico = 'sociedade' AND sociedade_id IS NOT NULL)"
            " OR (publico <> 'sociedade' AND sociedade_id IS NULL)",
            name="comunicado_sociedade",
        ),
        sa.CheckConstraint(
            "status <> 'agendado' OR publicar_em IS NOT NULL", name="comunicado_agendamento"
        ),
    )
    op.create_index("ix_comunicado_igreja_id", "comunicado", ["igreja_id"])
    op.create_index("ix_comunicado_sociedade_id", "comunicado", ["sociedade_id"])
    op.create_index("ix_comunicado_autor_id", "comunicado", ["autor_id"])


def downgrade() -> None:
    op.drop_table("comunicado")
