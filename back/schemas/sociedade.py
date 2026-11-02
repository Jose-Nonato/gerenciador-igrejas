import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.enums import CargoLideranca, SiglaSociedade, StatusPresenca, TipoSocio


def _nao_futura(valor: date | None) -> date | None:
    if valor is not None and valor > date.today():
        raise ValueError("A data não pode estar no futuro")
    return valor


# ---------- sociedade ----------

class SociedadeCreate(BaseModel):
    sigla: SiglaSociedade
    nome: str | None = Field(default=None, max_length=255)


class SociedadeUpdate(BaseModel):
    """Só o nome de exibição muda; `null` apaga o nome."""

    nome: str | None = Field(default=None, max_length=255)


class SociedadeOut(BaseModel):
    id: uuid.UUID
    sigla: SiglaSociedade
    nome: str | None
    total_socios: int = Field(description="Sócios que ainda participam (sem data de saída)")


# ---------- sócio ----------

class SocioCreate(BaseModel):
    """Sócio ativo e cooperador são membros da igreja (`membro_id`); `nao_membro` só tem nome."""

    tipo: TipoSocio
    membro_id: uuid.UUID | None = None
    nome_externo: str | None = Field(default=None, max_length=255)

    @field_validator("nome_externo")
    @classmethod
    def _limpa_nome(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None

    @model_validator(mode="after")
    def _identificacao(self):
        if self.tipo == TipoSocio.NAO_MEMBRO:
            if self.membro_id is not None:
                raise ValueError("Não membro não tem membro_id")
            if not self.nome_externo:
                raise ValueError("Informe o nome do não membro")
        else:
            if self.membro_id is None:
                raise ValueError("Informe o membro (membro_id)")
            if self.nome_externo is not None:
                raise ValueError("nome_externo só se aplica a não membro")
        return self


class SocioUpdate(BaseModel):
    """Ativo <-> cooperador, ou corrigir o nome de um não membro."""

    tipo: TipoSocio | None = None
    nome_externo: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def _algum_campo(self):
        if self.tipo is None and self.nome_externo is None:
            raise ValueError("Informe ao menos um campo: tipo ou nome_externo")
        return self


class SocioOut(BaseModel):
    id: uuid.UUID
    sociedade_id: uuid.UUID
    membro_id: uuid.UUID | None
    nome: str
    tipo: TipoSocio
    entrou_em: date
    saiu_em: date | None


# ---------- reunião e presença ----------

class PresencaItem(BaseModel):
    socio_id: uuid.UUID
    status: StatusPresenca


class PresencasLote(BaseModel):
    presencas: list[PresencaItem] = Field(max_length=500)

    @model_validator(mode="after")
    def _sem_repetidos(self):
        ids = [p.socio_id for p in self.presencas]
        if len(ids) != len(set(ids)):
            raise ValueError("Há sócios repetidos na lista de presenças")
        return self


class ReuniaoCreate(BaseModel):
    data: date
    tema: str | None = Field(default=None, max_length=255)
    presencas: list[PresencaItem] = Field(default_factory=list, max_length=500)

    _data = field_validator("data")(_nao_futura)

    @model_validator(mode="after")
    def _sem_repetidos(self):
        ids = [p.socio_id for p in self.presencas]
        if len(ids) != len(set(ids)):
            raise ValueError("Há sócios repetidos na lista de presenças")
        return self


class ReuniaoUpdate(BaseModel):
    data: date | None = None
    tema: str | None = Field(default=None, max_length=255)

    _data = field_validator("data")(_nao_futura)

    @model_validator(mode="after")
    def _algum_campo(self):
        if self.data is None and "tema" not in self.model_fields_set:
            raise ValueError("Informe ao menos um campo: data ou tema")
        return self


class ReuniaoOut(BaseModel):
    id: uuid.UUID
    sociedade_id: uuid.UUID
    data: date
    tema: str | None
    presentes: int
    ausentes: int
    justificados: int


class PresencaOut(BaseModel):
    socio_id: uuid.UUID
    nome: str
    status: StatusPresenca


class ReuniaoDetalheOut(ReuniaoOut):
    model_config = ConfigDict(from_attributes=True)

    presencas: list[PresencaOut]


# ---------- frequência ----------

class FrequenciaSocioOut(BaseModel):
    socio_id: uuid.UUID
    nome: str
    tipo: TipoSocio
    presentes: int
    ausentes: int
    justificados: int
    sem_registro: int = Field(description="Reuniões do período sem presença lançada para o sócio")
    percentual_presenca: float | None = Field(
        description="Presentes sobre as reuniões com lançamento (P+A+J), em %; "
        "nulo se não houver nenhum lançamento"
    )


class FrequenciaOut(BaseModel):
    de: date | None
    ate: date | None
    total_reunioes: int
    socios: list[FrequenciaSocioOut]


# ---------- liderança (diretoria) ----------

class LiderancaCreate(BaseModel):
    membro_id: uuid.UUID
    cargo: CargoLideranca
    cargo_descricao: str | None = Field(default=None, max_length=100)
    inicio: date | None = Field(default=None, description="Padrão: hoje")

    _inicio = field_validator("inicio")(_nao_futura)

    @field_validator("cargo_descricao")
    @classmethod
    def _limpa(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None

    @model_validator(mode="after")
    def _descricao(self):
        if self.cargo == CargoLideranca.OUTRO and not self.cargo_descricao:
            raise ValueError("Descreva o cargo (cargo_descricao)")
        if self.cargo != CargoLideranca.OUTRO and self.cargo_descricao:
            raise ValueError("cargo_descricao só se aplica ao cargo 'outro'")
        return self


class LiderancaUpdate(BaseModel):
    """Corrigir as datas ou encerrar o mandato (`fim`). O cargo e a pessoa não mudam:
    para trocar, encerre o mandato e registre outro."""

    inicio: date | None = None
    fim: date | None = None

    _datas = field_validator("inicio", "fim")(_nao_futura)

    @model_validator(mode="after")
    def _algum_campo(self):
        if self.inicio is None and self.fim is None:
            raise ValueError("Informe ao menos um campo: inicio ou fim")
        return self


class LiderancaOut(BaseModel):
    id: uuid.UUID
    sociedade_id: uuid.UUID
    membro_id: uuid.UUID
    nome: str
    cargo: CargoLideranca
    cargo_descricao: str | None
    inicio: date
    fim: date | None = Field(description="Nulo = em exercício")


class MembroResumo(BaseModel):
    """Só o necessário para escolher uma pessoa: o líder não vê os demais dados do membro."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    numero_rol: int | None
