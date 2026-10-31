import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import IgrejaScoped, UUIDPk


class LogAuditoria(UUIDPk, IgrejaScoped, Base):
    """Mudanças de perfil, senha e rol. `detalhes` guarda o antes/depois (acréscimo à planilha)."""

    __tablename__ = "log_auditoria"

    # SET NULL: o log sobrevive à remoção do usuário
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), index=True
    )
    acao: Mapped[str] = mapped_column(String(64), index=True)
    entidade: Mapped[str] = mapped_column(String(64))
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    detalhes: Mapped[dict | None] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
