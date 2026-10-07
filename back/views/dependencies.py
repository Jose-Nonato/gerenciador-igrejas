from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from controllers import AuthController, UserController
from core.database import get_db
from models import User
from repositories import RefreshTokenRepository, UserRepository

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_controller(db: DbSession) -> AuthController:
    return AuthController(UserRepository(db), RefreshTokenRepository(db))


def get_user_controller(db: DbSession) -> UserController:
    return UserController(UserRepository(db))


# Só documenta o esquema Bearer no OpenAPI (botão "Authorize" no /docs);
# a validação do token continua sendo feita pelo JWTAuthMiddleware.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    controller: Annotated[UserController, Depends(get_user_controller)],
    _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    return controller.get_authenticated_user(getattr(request.state, "user_id", None))


AuthCtrl = Annotated[AuthController, Depends(get_auth_controller)]
CurrentUser = Annotated[User, Depends(get_current_user)]
