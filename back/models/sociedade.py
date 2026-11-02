import uuid
from datetime import date, datetime

from sqlalchemy import (
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
from models.enums import (
    CARGOS_UNICOS,
    CargoLideranca,
    SiglaSociedade,
    StatusPresenca,
    TipoSocio,
    enum_column,
)


class Sociedade(UUIDPk, IgrejaScoped, Base):
    """Sociedade interna da igreja (UCP, UPA, UMP, SAF, UPH): no máximo uma de cada sigla."""

    __tablename__ = "sociedade"
    __table_args__ = (
        UniqueConstraint("igreja_id", "sigla", name="uq_sociedade_igreja_sigla"),
    )

    sigla: Mapped[SiglaSociedade] = mapped_column(enum_column(SiglaSociedade))
    # Nome de exibição opcional (ex.: "SAF Maria Madalena")
    nome: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Socio(UUIDPk, IgrejaScoped, Base):
    """Participação numa sociedade. Sair não apaga: `saiu_em` guarda a data e mantém a
    presença histórica. Sócio ativo ou cooperador é um membro da igreja; `nao_membro`
    (visitante frequente) só tem nome."""

    __tablename__ = "socio"
    __table_args__ = (
        CheckConstraint(
            "(tipo = 'nao_membro' AND membro_id IS NULL AND nome_externo IS NOT NULL)"
            " OR (tipo <> 'nao_membro' AND membro_id IS NOT NULL AND nome_externo IS NULL)",
            name="socio_identificacao",
        ),
        # Um membro não pode estar duas vezes ativo na mesma sociedade (pode voltar depois de sair)
        Index(
            "uq_socio_sociedade_membro_ativo",
            "sociedade_id",
            "membro_id",
            unique=True,
            postgresql_where=text("saiu_em IS NULL AND membro_id IS NOT NULL"),
        ),
    )

    sociedade_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sociedade.id", ondelete="RESTRICT"), index=True
    )
    membro_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("membro.id", ondelete="RESTRICT"), index=True
    )
    nome_externo: Mapped[str | None] = mapped_column(String(255))
    tipo: Mapped[TipoSocio] = mapped_column(enum_column(TipoSocio))
    entrou_em: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    saiu_em: Mapped[date | None] = mapped_column(Date)


class Reuniao(UUIDPk, IgrejaScoped, Base):
    __tablename__ = "reuniao"
    __table_args__ = (
        UniqueConstraint("sociedade_id", "data", name="uq_reuniao_sociedade_data"),
    )

    sociedade_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sociedade.id", ondelete="RESTRICT"), index=True
    )
    data: Mapped[date] = mapped_column(Date)
    tema: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Presenca(IgrejaScoped, Base):
    __tablename__ = "presenca"
    __table_args__ = (PrimaryKeyConstraint("reuniao_id", "socio_id", name="pk_presenca"),)

    reuniao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reuniao.id", ondelete="RESTRICT"))
    socio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("socio.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[StatusPresenca] = mapped_column(enum_column(StatusPresenca))


_UNICOS_SQL = ", ".join(repr(c.value) for c in sorted(CARGOS_UNICOS))


class Lideranca(UUIDPk, IgrejaScoped, Base):
    """Diretoria da sociedade: quem ocupa cada cargo e em que período. É só um registro:
    não concede permissão no sistema. Encerrar o mandato grava `fim` e mantém o histórico."""

    __tablename__ = "lideranca"
    __table_args__ = (
        CheckConstraint(
            "(cargo = 'outro' AND cargo_descricao IS NOT NULL)"
            " OR (cargo <> 'outro' AND cargo_descricao IS NULL)",
            name="lideranca_descricao",
        ),
        CheckConstraint("fim IS NULL OR fim >= inicio", name="lideranca_periodo"),
        # Presidente, vice, secretário e tesoureiro: só um em exercício por sociedade
        Index(
            "uq_lideranca_cargo_unico_ativo",
            "sociedade_id",
            "cargo",
            unique=True,
            postgresql_where=text(f"fim IS NULL AND cargo IN ({_UNICOS_SQL})"),
        ),
    )

    sociedade_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sociedade.id", ondelete="RESTRICT"), index=True
    )
    membro_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("membro.id", ondelete="RESTRICT"), index=True
    )
    cargo: Mapped[CargoLideranca] = mapped_column(enum_column(CargoLideranca))
    # Só para o cargo "outro" (ex.: "Diretor de música")
    cargo_descricao: Mapped[str | None] = mapped_column(String(100))
    inicio: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    fim: Mapped[date | None] = mapped_column(Date)
