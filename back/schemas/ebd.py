import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.enums import StatusPresenca


def _nao_futura(valor: date | None) -> date | None:
    if valor is not None and valor > date.today():
        raise ValueError("A data não pode estar no futuro")
    return valor


def _limpo(v: str | None) -> str | None:
    return v.strip() or None if v is not None else None


# ---------- classe ----------

class EbdClasseCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    faixa_etaria: str | None = Field(default=None, max_length=100)

    @field_validator("nome")
    @classmethod
    def _nome(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe o nome da classe")
        return v

    _faixa = field_validator("faixa_etaria")(_limpo)


class EbdClasseUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    faixa_etaria: str | None = Field(default=None, max_length=100)
    ativa: bool | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Informe o nome da classe")
        return v.strip() if v is not None else None

    _faixa = field_validator("faixa_etaria")(_limpo)

    @model_validator(mode="after")
    def _algum_campo(self):
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo")
        for campo in ("nome", "ativa"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo")
        return self


class EbdClasseOut(BaseModel):
    id: uuid.UUID
    nome: str
    faixa_etaria: str | None
    ativa: bool
    total_alunos: int = Field(description="Alunos que ainda participam (sem data de saída)")
    total_professores: int = Field(description="Professores em exercício")


# ---------- professor ----------

class EbdProfessorCreate(BaseModel):
    membro_id: uuid.UUID
    inicio: date | None = Field(default=None, description="Padrão: hoje")

    _inicio = field_validator("inicio")(_nao_futura)


class EbdProfessorUpdate(BaseModel):
    """Corrigir as datas ou encerrar o exercício (`fim`); o histórico é mantido."""

    inicio: date | None = None
    fim: date | None = None

    _datas = field_validator("inicio", "fim")(_nao_futura)

    @model_validator(mode="after")
    def _algum_campo(self):
        if self.inicio is None and self.fim is None:
            raise ValueError("Informe ao menos um campo: inicio ou fim")
        return self


class EbdProfessorOut(BaseModel):
    id: uuid.UUID
    classe_id: uuid.UUID
    membro_id: uuid.UUID
    nome: str
    inicio: date
    fim: date | None = Field(description="Nulo = em exercício")


# ---------- aluno ----------

class EbdAlunoCreate(BaseModel):
    """Membro da igreja (`membro_id`) ou visitante (`nome_externo`)."""

    membro_id: uuid.UUID | None = None
    nome_externo: str | None = Field(default=None, max_length=255)

    _nome = field_validator("nome_externo")(_limpo)

    @model_validator(mode="after")
    def _identificacao(self):
        if (self.membro_id is None) == (self.nome_externo is None):
            raise ValueError("Informe o membro (membro_id) ou o nome do visitante (nome_externo)")
        return self


class EbdAlunoUpdate(BaseModel):
    """Corrigir o nome de um visitante."""

    nome_externo: str = Field(min_length=1, max_length=255)


class EbdAlunoOut(BaseModel):
    id: uuid.UUID
    classe_id: uuid.UUID
    membro_id: uuid.UUID | None
    nome: str
    entrou_em: date
    saiu_em: date | None


# ---------- aula e presença ----------

class EbdPresencaItem(BaseModel):
    aluno_id: uuid.UUID
    status: StatusPresenca


def _sem_repetidos(itens: list[EbdPresencaItem]) -> None:
    ids = [p.aluno_id for p in itens]
    if len(ids) != len(set(ids)):
        raise ValueError("Há alunos repetidos na lista de presenças")


class EbdPresencasLote(BaseModel):
    presencas: list[EbdPresencaItem] = Field(max_length=500)

    @model_validator(mode="after")
    def _repetidos(self):
        _sem_repetidos(self.presencas)
        return self


class EbdAulaCreate(BaseModel):
    data: date
    licao: str | None = Field(default=None, max_length=255)
    presencas: list[EbdPresencaItem] = Field(default_factory=list, max_length=500)

    _data = field_validator("data")(_nao_futura)
    _licao = field_validator("licao")(_limpo)

    @model_validator(mode="after")
    def _repetidos(self):
        _sem_repetidos(self.presencas)
        return self


class EbdAulaUpdate(BaseModel):
    data: date | None = None
    licao: str | None = Field(default=None, max_length=255)

    _data = field_validator("data")(_nao_futura)
    _licao = field_validator("licao")(_limpo)

    @model_validator(mode="after")
    def _algum_campo(self):
        if self.data is None and "licao" not in self.model_fields_set:
            raise ValueError("Informe ao menos um campo: data ou licao")
        return self


class EbdAulaOut(BaseModel):
    id: uuid.UUID
    classe_id: uuid.UUID
    data: date
    licao: str | None
    presentes: int
    ausentes: int
    justificados: int


class EbdPresencaOut(BaseModel):
    aluno_id: uuid.UUID
    nome: str
    status: StatusPresenca


class EbdAulaDetalheOut(EbdAulaOut):
    model_config = ConfigDict(from_attributes=True)

    presencas: list[EbdPresencaOut]


# ---------- frequência ----------

class EbdFrequenciaAlunoOut(BaseModel):
    aluno_id: uuid.UUID
    nome: str
    presentes: int
    ausentes: int
    justificados: int
    sem_registro: int = Field(description="Aulas do período sem presença lançada para o aluno")
    percentual_presenca: float | None = Field(
        description="Presentes sobre as aulas com lançamento (P+A+J), em %; "
        "nulo se não houver nenhum lançamento"
    )


class EbdFrequenciaOut(BaseModel):
    de: date | None
    ate: date | None
    total_aulas: int
    alunos: list[EbdFrequenciaAlunoOut]
