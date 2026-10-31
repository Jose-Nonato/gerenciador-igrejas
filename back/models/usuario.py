import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import IgrejaScoped, UUIDPk
from models.enums import PerfilUsuario, StatusUsuario, enum_column

if TYPE_CHECKING:
    from models.refresh_token import RefreshToken


class Usuario(UUIDPk, IgrejaScoped, Base):
    __tablename__ = "usuario"

    # Um membro tem no máximo uma conta de acesso
    membro_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("membro.id", ondelete="SET NULL"), unique=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[PerfilUsuario] = mapped_column(
        enum_column(PerfilUsuario), default=PerfilUsuario.USUARIO
    )
    status: Mapped[StatusUsuario] = mapped_column(
        enum_column(StatusUsuario), default=StatusUsuario.ATIVO
    )
    troca_obrigatoria: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    tentativas_falhas: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
