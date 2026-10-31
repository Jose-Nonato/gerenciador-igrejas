from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import IgrejaScoped, UUIDPk


class Familia(UUIDPk, IgrejaScoped, Base):
    __tablename__ = "familia"

    nome: Mapped[str] = mapped_column(String(255))
    endereco: Mapped[str | None] = mapped_column(Text)
