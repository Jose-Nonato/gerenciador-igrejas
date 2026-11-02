import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import IgrejaScoped, UUIDPk
from models.enums import CategoriaPost, StatusPost, TipoPublico, enum_column


class Comunicado(UUIDPk, IgrejaScoped, Base):
    """Mural da igreja: avisos, eventos, mensagens pastorais e pedidos de oração.

    Nasce como rascunho e só aparece aos leitores depois de publicado. Agendar grava
    `publicar_em`: não há tarefa em segundo plano, o comunicado agendado passa a valer como
    publicado nas consultas assim que a hora chega. Excluir é lógico (`excluido_em`).
    """

    __tablename__ = "comunicado"
    __table_args__ = (
        # Público "sociedade" exige a sociedade; os demais não a têm
        CheckConstraint(
            "(publico = 'sociedade' AND sociedade_id IS NOT NULL)"
            " OR (publico <> 'sociedade' AND sociedade_id IS NULL)",
            name="comunicado_sociedade",
        ),
        CheckConstraint(
            "status <> 'agendado' OR publicar_em IS NOT NULL", name="comunicado_agendamento"
        ),
    )

    titulo: Mapped[str] = mapped_column(String(200))
    corpo: Mapped[str] = mapped_column(Text)
    categoria: Mapped[CategoriaPost] = mapped_column(enum_column(CategoriaPost))
    publico: Mapped[TipoPublico] = mapped_column(enum_column(TipoPublico))
    sociedade_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sociedade.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[StatusPost] = mapped_column(
        enum_column(StatusPost), default=StatusPost.RASCUNHO
    )
    # Agendado: quando passa a valer. Publicado direto: `publicado_em`.
    publicar_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    autor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), index=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
