import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IgrejaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    cnpj: str | None
    presbiterio: str | None
    endereco: str | None
    criado_em: datetime


class IgrejaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    cnpj: str | None = Field(default=None, max_length=18)
    presbiterio: str | None = Field(default=None, max_length=255)
    endereco: str | None = None
