import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from schemas import (
    EventoCreate,
    EventoOut,
    FiltroMembros,
    MembroCreate,
    MembroOut,
    MembroPage,
    MembroUpdate,
    RegistroEventoOut,
)
from views.dependencies import ActiveUser, MembroCtrl, StaffUser

router = APIRouter(prefix="/membros", tags=["membros"])

Filtro = Annotated[FiltroMembros, Query()]


@router.get("/me", response_model=MembroOut)
def meu_cadastro(user: ActiveUser, controller: MembroCtrl):
    return controller.get_meu(user)


@router.get("/exportar")
def exportar(ator: StaffUser, controller: MembroCtrl, filtro: Filtro):
    conteudo = controller.exportar_csv(ator, filtro)
    return Response(
        content=conteudo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="rol.csv"'},
    )


@router.get("", response_model=MembroPage)
def listar(ator: StaffUser, controller: MembroCtrl, filtro: Filtro):
    items, total = controller.buscar(ator, filtro)
    return {"items": items, "total": total, "limit": filtro.limit, "offset": filtro.offset}


@router.post("", response_model=MembroOut, status_code=status.HTTP_201_CREATED)
def criar(data: MembroCreate, ator: StaffUser, controller: MembroCtrl):
    return controller.criar(ator, data)


@router.get("/{membro_id}", response_model=MembroOut)
def obter(membro_id: uuid.UUID, ator: StaffUser, controller: MembroCtrl):
    return controller.get(ator, membro_id)


@router.patch("/{membro_id}", response_model=MembroOut)
def atualizar(membro_id: uuid.UUID, data: MembroUpdate, ator: StaffUser, controller: MembroCtrl):
    return controller.atualizar(ator, membro_id, data)


@router.get("/{membro_id}/eventos", response_model=list[EventoOut])
def listar_eventos(membro_id: uuid.UUID, ator: StaffUser, controller: MembroCtrl):
    return controller.eventos_do_membro(ator, membro_id)


@router.post(
    "/{membro_id}/eventos", response_model=RegistroEventoOut, status_code=status.HTTP_201_CREATED
)
def registrar_evento(
    membro_id: uuid.UUID, data: EventoCreate, ator: StaffUser, controller: MembroCtrl
):
    evento, membro = controller.registrar_evento(ator, membro_id, data)
    return {"evento": evento, "membro": membro}
