"""Fase 2b: exclusão lógica de membros (membro.excluido_em).

O número do rol passa a ser único só entre os cadastros não excluídos: o número de
um cadastro removido por engano volta a ficar livre.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("membro", sa.Column("excluido_em", sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint("uq_membro_igreja_numero_rol", "membro", type_="unique")
    op.create_index(
        "uq_membro_igreja_numero_rol",
        "membro",
        ["igreja_id", "numero_rol"],
        unique=True,
        postgresql_where=sa.text("excluido_em IS NULL"),
    )


def downgrade() -> None:
    # A restrição antiga vale para todas as linhas: cadastros excluídos que repetem um
    # número em uso perdem o número (a coluna aceita NULL) para ela poder ser recriada.
    op.execute(
        """
        UPDATE membro m SET numero_rol = NULL
        WHERE m.excluido_em IS NOT NULL AND EXISTS (
            SELECT 1 FROM membro o
            WHERE o.igreja_id = m.igreja_id AND o.numero_rol = m.numero_rol AND o.id <> m.id
        )
        """
    )
    op.drop_index("uq_membro_igreja_numero_rol", table_name="membro")
    op.create_unique_constraint("uq_membro_igreja_numero_rol", "membro", ["igreja_id", "numero_rol"])
    op.drop_column("membro", "excluido_em")
