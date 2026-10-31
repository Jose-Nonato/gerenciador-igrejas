from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from schemas import EsqueciSenha, PasswordChange, RedefinirSenha, RefreshRequest, TokenPair
from views.dependencies import AuthCtrl, CurrentUser, RedefinicaoCtrl

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], controller: AuthCtrl):
    # OAuth2PasswordRequestForm usa "username"; aqui ele é o e-mail
    return controller.login(form.username, form.password)


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, controller: AuthCtrl):
    return controller.refresh(data.refresh_token)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChange, user: CurrentUser, controller: AuthCtrl):
    controller.change_password(user, data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUser, controller: AuthCtrl):
    controller.logout(user)


@router.post("/esqueci-senha", status_code=status.HTTP_204_NO_CONTENT)
def esqueci_senha(data: EsqueciSenha, controller: RedefinicaoCtrl):
    controller.solicitar(data.email)


@router.post("/redefinir-senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(data: RedefinirSenha, controller: RedefinicaoCtrl):
    controller.redefinir(data.token, data.nova_senha)
