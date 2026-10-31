import uuid

from fastapi import APIRouter, status

from schemas import MeuPerfilUpdate, UsuarioCreate, UsuarioOut, UsuarioUpdate
from views.dependencies import ActiveUser, AdminUser, CurrentUser, StaffUser, UsuarioCtrl

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/me", response_model=UsuarioOut)
def read_me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UsuarioOut)
def update_me(data: MeuPerfilUpdate, user: ActiveUser, controller: UsuarioCtrl):
    return controller.atualizar_me(user, data)


@router.get("", response_model=list[UsuarioOut])
def listar(ator: StaffUser, controller: UsuarioCtrl):
    return controller.listar(ator)


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def convidar(data: UsuarioCreate, ator: AdminUser, controller: UsuarioCtrl):
    return controller.convidar(ator, data)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def atualizar(usuario_id: uuid.UUID, data: UsuarioUpdate, ator: AdminUser, controller: UsuarioCtrl):
    return controller.atualizar(ator, usuario_id, data)


@router.post("/{usuario_id}/convite", status_code=status.HTTP_204_NO_CONTENT)
def reenviar_convite(usuario_id: uuid.UUID, ator: AdminUser, controller: UsuarioCtrl):
    controller.reenviar_convite(ator, usuario_id)
