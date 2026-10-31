from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import UUIDPk


class Igreja(UUIDPk, Base):
    __tablename__ = "igreja"

    nome: Mapped[str] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(18))
    presbiterio: Mapped[str | None] = mapped_column(String(255))
    endereco: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
