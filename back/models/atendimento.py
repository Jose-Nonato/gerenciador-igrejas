import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import IgrejaScoped, UUIDPk
from models.enums import (
    CategoriaAtendimento,
    ModalidadeAtendimento,
    StatusAtendimento,
    enum_column,
)


class DisponibilidadeAtendimento(UUIDPk, IgrejaScoped, Base):
    """Janela semanal em que um oficial (pastor ou presbítero) atende conversas.

    `dia_semana` segue o Python: 0 = segunda ... 6 = domingo. Os horários são do relógio da
    igreja (`FUSO_HORARIO`). Os horários marcáveis são calculados a partir da janela
    (fatiada de `duracao_min` em `duracao_min`), nunca gravados.
    """

    __tablename__ = "disponibilidade_atendimento"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="disponibilidade_dia_semana"),
        CheckConstraint("hora_fim > hora_inicio", name="disponibilidade_horario"),
        CheckConstraint("duracao_min > 0", name="disponibilidade_duracao"),
    )

    oficial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="RESTRICT"), index=True
    )
    dia_semana: Mapped[int] = mapped_column(SmallInteger)
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fim: Mapped[time] = mapped_column(Time)
    duracao_min: Mapped[int] = mapped_column(SmallInteger)
    modalidade: Mapped[ModalidadeAtendimento] = mapped_column(enum_column(ModalidadeAtendimento))
    local: Mapped[str | None] = mapped_column(String(255))
    ativa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class Atendimento(UUIDPk, IgrejaScoped, Base):
    """Conversa de um membro com um oficial. O `assunto` é sigiloso: só o solicitante e o
    oficial o veem, e ele nunca vai para a auditoria."""

    __tablename__ = "atendimento"
    __table_args__ = (
        CheckConstraint("fim > inicio", name="atendimento_periodo"),
        CheckConstraint(
            "(proposta_inicio IS NULL) = (proposta_fim IS NULL)", name="atendimento_proposta"
        ),
        CheckConstraint(
            "proposta_modalidade IS NULL OR proposta_modalidade IN ('presencial', 'online', 'visita')",
            name="atendimento_proposta_modalidade",
        ),
        # O mesmo horário de um oficial não pode ser reservado duas vezes (vale também para
        # duas requisições simultâneas). Recusado, cancelado etc. liberam o horário.
        Index(
            "uq_atendimento_horario_ativo",
            "oficial_id",
            "inicio",
            unique=True,
            postgresql_where=text("status IN ('solicitado', 'confirmado')"),
        ),
    )

    solicitante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("membro.id", ondelete="RESTRICT"), index=True
    )
    oficial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="RESTRICT"), index=True
    )
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fim: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    modalidade: Mapped[ModalidadeAtendimento] = mapped_column(enum_column(ModalidadeAtendimento))
    local: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[StatusAtendimento] = mapped_column(
        enum_column(StatusAtendimento), default=StatusAtendimento.SOLICITADO
    )
    categoria: Mapped[CategoriaAtendimento] = mapped_column(enum_column(CategoriaAtendimento))
    assunto: Mapped[str | None] = mapped_column(Text)
    # Motivo da recusa ou do cancelamento
    justificativa: Mapped[str | None] = mapped_column(String(500))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Remarcação proposta pelo oficial (status `remarcacao`). O horário original continua em
    # `inicio`/`fim` até quem pediu a conversa aceitar; só então a proposta o substitui.
    proposta_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposta_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposta_modalidade: Mapped[str | None] = mapped_column(String(10))
    proposta_local: Mapped[str | None] = mapped_column(String(255))
    # Preenchido quando o lembrete por e-mail é enviado (uma vez só)
    lembrete_enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BloqueioAgenda(UUIDPk, IgrejaScoped, Base):
    """Período em que o oficial não atende (férias, viagem), em dias inteiros do relógio da
    igreja. Os dias bloqueados deixam de oferecer horários; as conversas já marcadas nesses dias
    não são mexidas sozinhas: o oficial decide se cancela ou remarca."""

    __tablename__ = "bloqueio_agenda"
    __table_args__ = (CheckConstraint("ate >= de", name="bloqueio_agenda_periodo"),)

    oficial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="RESTRICT"), index=True
    )
    de: Mapped[date] = mapped_column(Date)
    ate: Mapped[date] = mapped_column(Date)
    motivo: Mapped[str | None] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
