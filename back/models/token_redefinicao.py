import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import IgrejaScoped, UUIDPk


class TokenRedefinicao(UUIDPk, IgrejaScoped, Base):
    """Link de redefinição de senha (também usado no convite). Só o hash é guardado."""

    __tablename__ = "token_redefinicao"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
