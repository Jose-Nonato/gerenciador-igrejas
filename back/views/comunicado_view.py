import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, status

from models import Comunicado
from models.enums import CategoriaPost, StatusPost
from repositories import esta_publicado
from schemas import (
    ComunicadoCreate,
    ComunicadoOut,
    ComunicadoPage,
    ComunicadoUpdate,
    PublicarRequest,
)
from views.dependencies import ActiveUser, ComunicadoCtrl

# Mural: todo usuário lê o que foi publicado para o público dele. Escrevem admin e pastor
# (qualquer público) e a liderança de uma sociedade (só para ela); as regras ficam no controller.
router = APIRouter(prefix="/comunicados", tags=["comunicados"])


def _out(linha: tuple[Comunicado, str | None, str | None]) -> dict:
    c, sigla, autor = linha
    agora = datetime.now(timezone.utc)
    # Agendado cuja hora chegou vale como publicado
    efetivo = StatusPost.PUBLICADO if esta_publicado(c, agora) else c.status
    return {
        "id": c.id,
        "titulo": c.titulo,
        "corpo": c.corpo,
        "categoria": c.categoria,
        "publico": c.publico,
        "sociedade_id": c.sociedade_id,
        "sociedade_sigla": sigla,
        "status": efetivo,
        "publicar_em": c.publicar_em,
        "data_publicacao": c.publicado_em or c.publicar_em,
        "autor": autor,
        "criado_em": c.criado_em,
        "atualizado_em": c.atualizado_em,
    }


def _pagina(resultado, limit: int, offset: int) -> dict:
    linhas, total = resultado
    return {"items": [_out(l) for l in linhas], "total": total, "limit": limit, "offset": offset}


@router.get("", response_model=ComunicadoPage)
def mural(
    ator: ActiveUser,
    controller: ComunicadoCtrl,
    categoria: CategoriaPost | None = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """O que foi publicado para o público do usuário, do mais recente ao mais antigo."""
    return _pagina(controller.mural(ator, categoria, limit, offset), limit, offset)


# Antes de "/{comunicado_id}", senão "gerenciar" seria lido como id
@router.get("/gerenciar", response_model=ComunicadoPage)
def gerenciar(
    ator: ActiveUser,
    controller: ComunicadoCtrl,
    status_: StatusPost | None = Query(None, alias="status"),
    categoria: CategoriaPost | None = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """Lista de quem escreve, com rascunhos e agendados. Admin e pastor veem todos; a
    liderança, só os da sua sociedade."""
    return _pagina(controller.gerenciar(ator, status_, categoria, limit, offset), limit, offset)


@router.post("", response_model=ComunicadoOut, status_code=status.HTTP_201_CREATED)
def criar(data: ComunicadoCreate, ator: ActiveUser, controller: ComunicadoCtrl):
    return _out(controller.criar(ator, data))


@router.get("/{comunicado_id}", response_model=ComunicadoOut)
def obter(comunicado_id: uuid.UUID, ator: ActiveUser, controller: ComunicadoCtrl):
    return _out(controller.get(ator, comunicado_id))


@router.patch("/{comunicado_id}", response_model=ComunicadoOut)
def atualizar(
    comunicado_id: uuid.UUID, data: ComunicadoUpdate, ator: ActiveUser, controller: ComunicadoCtrl
):
    return _out(controller.atualizar(ator, comunicado_id, data))


@router.post("/{comunicado_id}/publicar", response_model=ComunicadoOut)
def publicar(
    comunicado_id: uuid.UUID, data: PublicarRequest, ator: ActiveUser, controller: ComunicadoCtrl
):
    """Publica agora ou agenda para o futuro (`quando`)."""
    return _out(controller.publicar(ator, comunicado_id, data))


@router.post("/{comunicado_id}/despublicar", response_model=ComunicadoOut)
def despublicar(comunicado_id: uuid.UUID, ator: ActiveUser, controller: ComunicadoCtrl):
    """Volta para rascunho (também cancela um agendamento)."""
    return _out(controller.despublicar(ator, comunicado_id))


@router.delete("/{comunicado_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(comunicado_id: uuid.UUID, ator: ActiveUser, controller: ComunicadoCtrl):
    """Exclusão lógica."""
    controller.excluir(ator, comunicado_id)
