import uuid
from datetime import date, datetime, time

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from models.enums import (
    CategoriaAtendimento,
    ModalidadeAtendimento,
    PerfilUsuario,
    StatusAtendimento,
)


def _limpo(v: str | None) -> str | None:
    return v.strip() or None if v is not None else None


def _sem_segundos(v: time | None) -> time | None:
    return v.replace(second=0, microsecond=0, tzinfo=None) if v is not None else None


# ---------- disponibilidade ----------

class DisponibilidadeCreate(BaseModel):
    # 0 = segunda ... 6 = domingo
    dia_semana: int = Field(ge=0, le=6)
    hora_inicio: time
    hora_fim: time
    duracao_min: int = Field(ge=10, le=240)
    modalidade: ModalidadeAtendimento
    local: str | None = Field(default=None, max_length=255)

    _hi = field_validator("hora_inicio", "hora_fim")(_sem_segundos)
    _local = field_validator("local")(_limpo)

    @model_validator(mode="after")
    def _janela(self):
        minutos = (
            self.hora_fim.hour * 60 + self.hora_fim.minute
            - self.hora_inicio.hour * 60 - self.hora_inicio.minute
        )
        if minutos <= 0:
            raise ValueError("O fim deve ser depois do início")
        if minutos < self.duracao_min:
            raise ValueError("A janela é menor que a duração do atendimento")
        return self


class DisponibilidadeUpdate(BaseModel):
    dia_semana: int | None = Field(default=None, ge=0, le=6)
    hora_inicio: time | None = None
    hora_fim: time | None = None
    duracao_min: int | None = Field(default=None, ge=10, le=240)
    modalidade: ModalidadeAtendimento | None = None
    local: str | None = Field(default=None, max_length=255)
    ativa: bool | None = None

    _hi = field_validator("hora_inicio", "hora_fim")(_sem_segundos)
    _local = field_validator("local")(_limpo)

    @model_validator(mode="after")
    def _nao_vazio(self):
        # Campos obrigatórios no banco não aceitam null
        for campo in ("dia_semana", "hora_inicio", "hora_fim", "duracao_min", "modalidade", "ativa"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo")
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo")
        return self


class DisponibilidadeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    oficial_id: uuid.UUID
    dia_semana: int
    hora_inicio: time
    hora_fim: time
    duracao_min: int
    modalidade: ModalidadeAtendimento
    local: str | None
    ativa: bool


# ---------- oficiais e horários ----------

class OficialOut(BaseModel):
    id: uuid.UUID
    nome: str
    perfil: PerfilUsuario


class HorarioOut(BaseModel):
    inicio: datetime
    fim: datetime
    modalidade: ModalidadeAtendimento
    local: str | None


# ---------- atendimento ----------

class AtendimentoCreate(BaseModel):
    oficial_id: uuid.UUID
    inicio: AwareDatetime
    categoria: CategoriaAtendimento
    assunto: str | None = Field(default=None, max_length=2000)

    _assunto = field_validator("assunto")(_limpo)


class JustificativaIn(BaseModel):
    justificativa: str | None = Field(default=None, max_length=500)

    _j = field_validator("justificativa")(_limpo)


class AtendimentoOut(BaseModel):
    id: uuid.UUID
    solicitante_id: uuid.UUID
    solicitante_nome: str
    oficial_id: uuid.UUID
    oficial_nome: str
    inicio: datetime
    fim: datetime
    modalidade: ModalidadeAtendimento
    local: str | None
    status: StatusAtendimento
    categoria: CategoriaAtendimento
    assunto: str | None
    justificativa: str | None
    # Preenchidos só enquanto o oficial espera a resposta a uma remarcação (status `remarcacao`)
    proposta_inicio: datetime | None
    proposta_fim: datetime | None
    proposta_modalidade: ModalidadeAtendimento | None
    proposta_local: str | None
    criado_em: datetime


class RemarcacaoIn(BaseModel):
    inicio: AwareDatetime


# ---------- bloqueios de agenda ----------

_MAX_BLOQUEIO_DIAS = 366


class BloqueioCreate(BaseModel):
    de: date
    ate: date
    motivo: str | None = Field(default=None, max_length=200)

    _motivo = field_validator("motivo")(_limpo)

    @model_validator(mode="after")
    def _periodo(self):
        if self.ate < self.de:
            raise ValueError("O fim não pode ser antes do início")
        if (self.ate - self.de).days >= _MAX_BLOQUEIO_DIAS:
            raise ValueError("O período é longo demais (no máximo um ano)")
        return self


class BloqueioOut(BaseModel):
    id: uuid.UUID
    de: date
    ate: date
    motivo: str | None
    # Conversas ativas (pendentes, confirmadas ou com remarcação em aberto) que caem no período
    atendimentos_afetados: int


# ---------- relatório do oficial ----------

class RelatorioMesOut(BaseModel):
    mes: str  # 'AAAA-MM'
    total: int
    realizados: int
    faltas: int
    cancelados: int
    recusados: int
    em_andamento: int
