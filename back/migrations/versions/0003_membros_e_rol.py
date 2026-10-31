"""Fase 2: familia, membro e evento_eclesiastico; usuario.membro_id passa a ter FK.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

ROL = ("C", "NC")
SEXO = ("masculino", "feminino")
ESTADO_CIVIL = ("solteiro", "casado", "viuvo", "divorciado")
SITUACAO = ("ativo", "em_disciplina", "transferido", "falecido", "excluido")
OFICIO = ("nenhum", "presbitero", "diacono")
TIPO_EVENTO = (
    "batismo", "profissao_fe", "recepcao", "ordenacao", "disciplina", "restauracao", "saida",
)
FORMA_RECEPCAO = ("transferencia", "jurisdicao", "profissao_fe", "batismo_profissao_fe")


def _in(coluna: str, valores: tuple[str, ...]) -> str:
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


def _igreja_fk() -> sa.Column:
    return sa.Column(
        "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "familia",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("endereco", sa.Text()),
    )
    op.create_index("ix_familia_igreja_id", "familia", ["igreja_id"])

    op.create_table(
        "membro",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        sa.Column("familia_id", sa.Uuid(), sa.ForeignKey("familia.id", ondelete="SET NULL")),
        sa.Column("numero_rol", sa.Integer()),
        sa.Column("rol", sa.String(2), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("data_nascimento", sa.Date()),
        sa.Column("sexo", sa.String(9)),
        sa.Column("estado_civil", sa.String(10)),
        sa.Column("telefone", sa.String(32)),
        sa.Column("email", sa.String(255)),
        sa.Column("endereco", sa.Text()),
        sa.Column("situacao", sa.String(13), nullable=False),
        sa.Column("oficio", sa.String(10), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("igreja_id", "numero_rol", name="uq_membro_igreja_numero_rol"),
        sa.CheckConstraint(_in("rol", ROL), name="rol"),
        sa.CheckConstraint(_in("sexo", SEXO), name="sexo"),
        sa.CheckConstraint(_in("estado_civil", ESTADO_CIVIL), name="estadocivil"),
        sa.CheckConstraint(_in("situacao", SITUACAO), name="situacaomembro"),
        sa.CheckConstraint(_in("oficio", OFICIO), name="oficio"),
    )
    op.create_index("ix_membro_igreja_id", "membro", ["igreja_id"])
    op.create_index("ix_membro_familia_id", "membro", ["familia_id"])

    op.create_table(
        "evento_eclesiastico",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _igreja_fk(),
        sa.Column(
            "membro_id", sa.Uuid(), sa.ForeignKey("membro.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("forma_recepcao", sa.String(20)),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("ata_conselho", sa.String(255)),
        sa.Column("igreja_relacionada", sa.String(255)),
        sa.Column("observacao", sa.Text()),
        sa.Column("oficio", sa.String(10)),
        sa.Column("situacao_resultante", sa.String(13)),
        sa.CheckConstraint(_in("tipo", TIPO_EVENTO), name="tipoeventoeclesiastico"),
        sa.CheckConstraint(_in("forma_recepcao", FORMA_RECEPCAO), name="formarecepcao"),
        sa.CheckConstraint(_in("oficio", OFICIO), name="oficio"),
        sa.CheckConstraint(_in("situacao_resultante", SITUACAO), name="situacaomembro"),
    )
    op.create_index("ix_evento_eclesiastico_igreja_id", "evento_eclesiastico", ["igreja_id"])
    op.create_index("ix_evento_eclesiastico_membro_id", "evento_eclesiastico", ["membro_id"])

    # usuario.membro_id: agora com FK e no máximo uma conta por membro
    op.drop_index("ix_usuario_membro_id", table_name="usuario")
    op.create_index("ix_usuario_membro_id", "usuario", ["membro_id"], unique=True)
    op.create_foreign_key(
        "usuario_membro_id_fkey", "usuario", "membro", ["membro_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("usuario_membro_id_fkey", "usuario", type_="foreignkey")
    op.drop_index("ix_usuario_membro_id", table_name="usuario")
    op.create_index("ix_usuario_membro_id", "usuario", ["membro_id"])
    op.drop_table("evento_eclesiastico")
    op.drop_table("membro")
    op.drop_table("familia")
