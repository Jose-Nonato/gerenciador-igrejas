import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import IgrejaScoped, UUIDPk
from models.enums import EstadoCivil, Oficio, Rol, Sexo, SituacaoMembro, enum_column


class Membro(UUIDPk, IgrejaScoped, Base):
    """Rol de membros. Nunca é apagado: a situação muda por evento eclesiástico."""

    __tablename__ = "membro"
    __table_args__ = (
        UniqueConstraint("igreja_id", "numero_rol", name="uq_membro_igreja_numero_rol"),
    )

    familia_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("familia.id", ondelete="SET NULL"), index=True
    )
    numero_rol: Mapped[int | None] = mapped_column(Integer)
    rol: Mapped[Rol] = mapped_column(enum_column(Rol))
    nome: Mapped[str] = mapped_column(String(255))
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    sexo: Mapped[Sexo | None] = mapped_column(enum_column(Sexo))
    estado_civil: Mapped[EstadoCivil | None] = mapped_column(enum_column(EstadoCivil))
    telefone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    endereco: Mapped[str | None] = mapped_column(Text)
    situacao: Mapped[SituacaoMembro] = mapped_column(
        enum_column(SituacaoMembro), default=SituacaoMembro.ATIVO
    )
    oficio: Mapped[Oficio] = mapped_column(enum_column(Oficio), default=Oficio.NENHUM)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
