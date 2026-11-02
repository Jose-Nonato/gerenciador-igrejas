import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from models.enums import (
    EstadoCivil,
    FormaRecepcao,
    Oficio,
    PerfilUsuario,
    Rol,
    Sexo,
    SituacaoMembro,
    StatusUsuario,
    TipoEventoEclesiastico,
)


def _nao_futura(valor: date | None) -> date | None:
    if valor is not None and valor > date.today():
        raise ValueError("A data não pode estar no futuro")
    return valor


# ---------- família ----------

class FamiliaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    endereco: str | None = None


class FamiliaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    endereco: str | None = None


class FamiliaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    endereco: str | None


# ---------- membro ----------

class MembroCreate(BaseModel):
    """Cadastro inicial. `rol`, `situacao` e `oficio` só são definidos aqui;
    depois mudam por evento eclesiástico."""

    nome: str = Field(min_length=1, max_length=255)
    rol: Rol
    familia_id: uuid.UUID | None = None
    numero_rol: int | None = Field(default=None, ge=1)
    data_nascimento: date | None = None
    sexo: Sexo | None = None
    estado_civil: EstadoCivil | None = None
    telefone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    endereco: str | None = None
    situacao: SituacaoMembro = SituacaoMembro.ATIVO
    oficio: Oficio = Oficio.NENHUM

    _data = field_validator("data_nascimento")(_nao_futura)


class MembroUpdate(BaseModel):
    """Dados cadastrais. Rol, situação e ofício não passam por aqui (use eventos)."""

    nome: str | None = Field(default=None, min_length=1, max_length=255)
    familia_id: uuid.UUID | None = None
    numero_rol: int | None = Field(default=None, ge=1)
    data_nascimento: date | None = None
    sexo: Sexo | None = None
    estado_civil: EstadoCivil | None = None
    telefone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    endereco: str | None = None

    _data = field_validator("data_nascimento")(_nao_futura)


class AcessoOut(BaseModel):
    """Conta de acesso ao sistema ligada ao membro."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    perfil: PerfilUsuario
    status: StatusUsuario


class MembroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    familia_id: uuid.UUID | None
    numero_rol: int | None
    rol: Rol
    nome: str
    data_nascimento: date | None
    sexo: Sexo | None
    estado_civil: EstadoCivil | None
    telefone: str | None
    email: str | None
    endereco: str | None
    situacao: SituacaoMembro
    oficio: Oficio
    criado_em: datetime
    atualizado_em: datetime
    acesso: AcessoOut | None = None


class FiltroMembros(BaseModel):
    q: str | None = Field(default=None, max_length=100, description="Parte do nome")
    rol: Rol | None = None
    situacao: SituacaoMembro | None = None
    oficio: Oficio | None = None
    familia_id: uuid.UUID | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class MembroPage(BaseModel):
    items: list[MembroOut]
    total: int
    limit: int
    offset: int


# ---------- evento eclesiástico ----------

class EventoCreate(BaseModel):
    tipo: TipoEventoEclesiastico
    data: date
    ata_conselho: str | None = Field(default=None, max_length=255)
    forma_recepcao: FormaRecepcao | None = None
    igreja_relacionada: str | None = Field(default=None, max_length=255)
    observacao: str | None = None
    # Só para ordenação (ofício conferido) e saída (motivo)
    oficio: Oficio | None = None
    situacao_resultante: SituacaoMembro | None = None

    _data = field_validator("data")(_nao_futura)


class EventoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    membro_id: uuid.UUID
    tipo: TipoEventoEclesiastico
    forma_recepcao: FormaRecepcao | None
    data: date
    ata_conselho: str | None
    igreja_relacionada: str | None
    observacao: str | None
    oficio: Oficio | None
    situacao_resultante: SituacaoMembro | None


class RegistroEventoOut(BaseModel):
    """Evento gravado e o membro já com os efeitos aplicados."""

    evento: EventoOut
    membro: MembroOut
