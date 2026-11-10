import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import IgrejaScoped, UUIDPk
from models.enums import StatusPresenca, enum_column


class EbdClasse(UUIDPk, IgrejaScoped, Base):
    """Classe (turma) da Escola Bíblica Dominical. Desativar não apaga: o histórico fica."""

    __tablename__ = "ebd_classe"
    __table_args__ = (UniqueConstraint("igreja_id", "nome", name="uq_ebd_classe_igreja_nome"),)

    nome: Mapped[str] = mapped_column(String(100))
    # Texto livre (ex.: "Adolescentes, 12 a 17 anos")
    faixa_etaria: Mapped[str | None] = mapped_column(String(100))
    ativa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EbdProfessor(UUIDPk, IgrejaScoped, Base):
    """Professor de uma classe (sempre membro). Encerrar grava `fim` e mantém o histórico."""

    __tablename__ = "ebd_professor"
    __table_args__ = (
        CheckConstraint("fim IS NULL OR fim >= inicio", name="ebd_professor_periodo"),
        # O mesmo membro não pode estar duas vezes em exercício na mesma classe
        Index(
            "uq_ebd_professor_ativo",
            "classe_id",
            "membro_id",
            unique=True,
            postgresql_where=text("fim IS NULL"),
        ),
    )

    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ebd_classe.id", ondelete="RESTRICT"), index=True
    )
    membro_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("membro.id", ondelete="RESTRICT"), index=True
    )
    inicio: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    fim: Mapped[date | None] = mapped_column(Date)


class EbdAluno(UUIDPk, IgrejaScoped, Base):
    """Matrícula numa classe. Membro da igreja (`membro_id`) ou visitante (`nome_externo`).
    Sair não apaga: `saiu_em` guarda a data e mantém a presença histórica."""

    __tablename__ = "ebd_aluno"
    __table_args__ = (
        CheckConstraint(
            "(membro_id IS NULL AND nome_externo IS NOT NULL)"
            " OR (membro_id IS NOT NULL AND nome_externo IS NULL)",
            name="ebd_aluno_identificacao",
        ),
        Index(
            "uq_ebd_aluno_ativo",
            "classe_id",
            "membro_id",
            unique=True,
            postgresql_where=text("saiu_em IS NULL AND membro_id IS NOT NULL"),
        ),
    )

    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ebd_classe.id", ondelete="RESTRICT"), index=True
    )
    membro_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("membro.id", ondelete="RESTRICT"), index=True
    )
    nome_externo: Mapped[str | None] = mapped_column(String(255))
    entrou_em: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    saiu_em: Mapped[date | None] = mapped_column(Date)


class EbdAula(UUIDPk, IgrejaScoped, Base):
    __tablename__ = "ebd_aula"
    __table_args__ = (UniqueConstraint("classe_id", "data", name="uq_ebd_aula_classe_data"),)

    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ebd_classe.id", ondelete="RESTRICT"), index=True
    )
    data: Mapped[date] = mapped_column(Date)
    # Lição ou tema do dia
    licao: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EbdPresenca(IgrejaScoped, Base):
    __tablename__ = "ebd_presenca"
    __table_args__ = (PrimaryKeyConstraint("aula_id", "aluno_id", name="pk_ebd_presenca"),)

    aula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ebd_aula.id", ondelete="RESTRICT"))
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ebd_aluno.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[StatusPresenca] = mapped_column(enum_column(StatusPresenca))
