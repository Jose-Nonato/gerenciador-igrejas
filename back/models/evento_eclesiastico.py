import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import IgrejaScoped, UUIDPk
from models.enums import (
    FormaRecepcao,
    Oficio,
    SituacaoMembro,
    TipoEventoEclesiastico,
    enum_column,
)


class EventoEclesiastico(UUIDPk, IgrejaScoped, Base):
    """Histórico do membro: batismo, profissão de fé, recepção, ordenação, disciplina, saída.

    `oficio` e `situacao_resultante` são acréscimos à planilha: sem eles o histórico
    não diz qual ofício foi conferido nem o motivo de uma saída.
    """

    __tablename__ = "evento_eclesiastico"

    # RESTRICT: o membro não pode ser apagado enquanto tiver histórico
    membro_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("membro.id", ondelete="RESTRICT"), index=True
    )
    tipo: Mapped[TipoEventoEclesiastico] = mapped_column(enum_column(TipoEventoEclesiastico))
    forma_recepcao: Mapped[FormaRecepcao | None] = mapped_column(enum_column(FormaRecepcao))
    data: Mapped[date] = mapped_column(Date)
    ata_conselho: Mapped[str | None] = mapped_column(String(255))
    igreja_relacionada: Mapped[str | None] = mapped_column(String(255))
    observacao: Mapped[str | None] = mapped_column(Text)
    oficio: Mapped[Oficio | None] = mapped_column(enum_column(Oficio))
    situacao_resultante: Mapped[SituacaoMembro | None] = mapped_column(
        enum_column(SituacaoMembro)
    )
