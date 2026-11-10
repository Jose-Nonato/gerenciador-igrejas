import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from models.enums import CategoriaPost, StatusPost, TipoPublico

Titulo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Corpo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


class ComunicadoCreate(BaseModel):
    """Todo comunicado nasce como rascunho; publicar ou agendar é uma ação à parte."""

    titulo: Titulo
    corpo: Corpo
    categoria: CategoriaPost
    publico: TipoPublico
    sociedade_id: uuid.UUID | None = Field(
        default=None, description="Obrigatório (e só aceito) quando o público é 'sociedade'"
    )

    @model_validator(mode="after")
    def _sociedade(self):
        if self.publico == TipoPublico.SOCIEDADE and self.sociedade_id is None:
            raise ValueError("Informe a sociedade (sociedade_id)")
        if self.publico != TipoPublico.SOCIEDADE and self.sociedade_id is not None:
            raise ValueError("sociedade_id só se aplica ao público 'sociedade'")
        return self


class ComunicadoUpdate(BaseModel):
    """Alteração parcial. Mudar o público para outro que não 'sociedade' limpa a sociedade."""

    titulo: Titulo | None = None
    corpo: Corpo | None = None
    categoria: CategoriaPost | None = None
    publico: TipoPublico | None = None
    sociedade_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _algum_campo(self):
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo")
        for campo in ("titulo", "corpo", "categoria", "publico"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo")
        return self


class PublicarRequest(BaseModel):
    quando: datetime | None = Field(
        default=None,
        description="Omitido ou no passado: publica agora. No futuro: agenda (informe o fuso, "
        "ex.: 2026-12-01T09:00:00-03:00; sem fuso é lido como UTC).",
    )


class ComunicadoOut(BaseModel):
    id: uuid.UUID
    titulo: str
    corpo: str
    categoria: CategoriaPost
    publico: TipoPublico
    sociedade_id: uuid.UUID | None
    sociedade_sigla: str | None
    tem_imagem: bool = Field(description="Baixe a imagem em GET /comunicados/{id}/imagem")
    status: StatusPost = Field(
        description="Efetivo: um comunicado agendado cuja hora já chegou aparece como publicado"
    )
    publicar_em: datetime | None
    data_publicacao: datetime | None = Field(
        description="Quando foi (ou será) publicado; nulo no rascunho"
    )
    autor: str | None
    criado_em: datetime
    atualizado_em: datetime


class ComunicadoPage(BaseModel):
    items: list[ComunicadoOut]
    total: int
    limit: int
    offset: int
