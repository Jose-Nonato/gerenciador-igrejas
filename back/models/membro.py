import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import IgrejaScoped, UUIDPk
from models.enums import EstadoCivil, Oficio, Rol, Sexo, SituacaoMembro, enum_column


class Membro(UUIDPk, IgrejaScoped, Base):
    """Rol de membros.

    A situação (transferido, falecido, excluído…) muda por evento eclesiástico e o membro
    continua no rol. `excluido_em` é outra coisa: remove um cadastro feito por engano
    (exclusão lógica). A linha, os eventos e a auditoria permanecem no banco.
    """

    __tablename__ = "membro"
    __table_args__ = (
        # Parcial: o número de um cadastro excluído volta a ficar livre
        Index(
            "uq_membro_igreja_numero_rol",
            "igreja_id",
            "numero_rol",
            unique=True,
            postgresql_where=text("excluido_em IS NULL"),
        ),
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
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Conta de acesso ligada a este membro (no máximo uma). Só leitura: o vínculo é gravado
    # pelo lado do usuário (`usuario.membro_id`).
    usuario: Mapped["Usuario | None"] = relationship(
        "Usuario",
        primaryjoin="Membro.id == foreign(Usuario.membro_id)",
        uselist=False,
        viewonly=True,
        lazy="selectin",
    )

    @property
    def acesso(self) -> "Usuario | None":
        """Resumo do acesso ao sistema (ou None se o membro não tem conta)."""
        return self.usuario
