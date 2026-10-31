import uuid

from fastapi import APIRouter, status

from schemas import FamiliaCreate, FamiliaOut, FamiliaUpdate
from views.dependencies import FamiliaCtrl, StaffUser

router = APIRouter(prefix="/familias", tags=["familias"])


@router.get("", response_model=list[FamiliaOut])
def listar(ator: StaffUser, controller: FamiliaCtrl):
    return controller.listar(ator)


@router.post("", response_model=FamiliaOut, status_code=status.HTTP_201_CREATED)
def criar(data: FamiliaCreate, ator: StaffUser, controller: FamiliaCtrl):
    return controller.criar(ator, data)


@router.get("/{familia_id}", response_model=FamiliaOut)
def obter(familia_id: uuid.UUID, ator: StaffUser, controller: FamiliaCtrl):
    return controller.get(ator, familia_id)


@router.patch("/{familia_id}", response_model=FamiliaOut)
def atualizar(familia_id: uuid.UUID, data: FamiliaUpdate, ator: StaffUser, controller: FamiliaCtrl):
    return controller.atualizar(ator, familia_id, data)


@router.delete("/{familia_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(familia_id: uuid.UUID, ator: StaffUser, controller: FamiliaCtrl):
    controller.excluir(ator, familia_id)
