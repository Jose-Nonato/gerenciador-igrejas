"""Fase 1: igreja, usuario, token_redefinicao e log_auditoria (substitui users).

Usuários existentes viram `usuario` com perfil admin, numa igreja
"Igreja (migrada)" criada só quando já havia usuários.

Revision ID: 0002
Revises: 0001
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

PERFIS = ("admin", "pastor", "presbitero", "usuario")
STATUS = ("ativo", "bloqueado", "convite_pendente", "desativado")


def _in(coluna: str, valores: tuple[str, ...]) -> str:
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


def upgrade() -> None:
    op.create_table(
        "igreja",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cnpj", sa.String(18)),
        sa.Column("presbiterio", sa.String(255)),
        sa.Column("endereco", sa.Text()),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "usuario",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("membro_id", sa.Uuid()),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("perfil", sa.String(10), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("troca_obrigatoria", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("tentativas_falhas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ultimo_acesso", sa.DateTime(timezone=True)),
        sa.CheckConstraint(_in("perfil", PERFIS), name="perfilusuario"),
        sa.CheckConstraint(_in("status", STATUS), name="statususuario"),
    )
    op.create_index("ix_usuario_igreja_id", "usuario", ["igreja_id"])
    op.create_index("ix_usuario_membro_id", "usuario", ["membro_id"])
    op.create_index("ix_usuario_email", "usuario", ["email"], unique=True)

    op.create_table(
        "token_redefinicao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_em", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_token_redefinicao_igreja_id", "token_redefinicao", ["igreja_id"])
    op.create_index("ix_token_redefinicao_usuario_id", "token_redefinicao", ["usuario_id"])
    op.create_index("ix_token_redefinicao_token_hash", "token_redefinicao", ["token_hash"], unique=True)

    op.create_table(
        "log_auditoria",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "igreja_id", sa.Uuid(), sa.ForeignKey("igreja.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id", ondelete="SET NULL")
        ),
        sa.Column("acao", sa.String(64), nullable=False),
        sa.Column("entidade", sa.String(64), nullable=False),
        sa.Column("entidade_id", sa.Uuid()),
        sa.Column("detalhes", postgresql.JSONB()),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_log_auditoria_igreja_id", "log_auditoria", ["igreja_id"])
    op.create_index("ix_log_auditoria_usuario_id", "log_auditoria", ["usuario_id"])
    op.create_index("ix_log_auditoria_acao", "log_auditoria", ["acao"])
    op.create_index("ix_log_auditoria_entidade_id", "log_auditoria", ["entidade_id"])

    # --- dados: users -> usuario ---
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT count(*) FROM users")).scalar():
        igreja_id = uuid.uuid4()
        conn.execute(
            sa.text("INSERT INTO igreja (id, nome) VALUES (:id, 'Igreja (migrada)')"),
            {"id": igreja_id},
        )
        conn.execute(
            sa.text(
                "INSERT INTO usuario (id, igreja_id, email, senha_hash, perfil, status) "
                "SELECT id, :igreja_id, email, hashed_password, 'admin', "
                "CASE WHEN is_active THEN 'ativo' ELSE 'desativado' END FROM users"
            ),
            {"igreja_id": igreja_id},
        )

    # --- refresh_tokens passa a apontar para usuario ---
    op.drop_constraint("refresh_tokens_user_id_fkey", "refresh_tokens", type_="foreignkey")
    op.alter_column("refresh_tokens", "user_id", new_column_name="usuario_id")
    op.execute("ALTER INDEX ix_refresh_tokens_user_id RENAME TO ix_refresh_tokens_usuario_id")
    op.create_foreign_key(
        "refresh_tokens_usuario_id_fkey",
        "refresh_tokens", "usuario", ["usuario_id"], ["id"], ondelete="CASCADE",
    )
    op.drop_table("users")


def downgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.execute(
        "INSERT INTO users (id, email, hashed_password, is_active) "
        "SELECT id, email, senha_hash, status = 'ativo' FROM usuario"
    )

    op.drop_constraint("refresh_tokens_usuario_id_fkey", "refresh_tokens", type_="foreignkey")
    op.alter_column("refresh_tokens", "usuario_id", new_column_name="user_id")
    op.execute("ALTER INDEX ix_refresh_tokens_usuario_id RENAME TO ix_refresh_tokens_user_id")
    op.create_foreign_key(
        "refresh_tokens_user_id_fkey",
        "refresh_tokens", "users", ["user_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_table("log_auditoria")
    op.drop_table("token_redefinicao")
    op.drop_table("usuario")
    op.drop_table("igreja")
