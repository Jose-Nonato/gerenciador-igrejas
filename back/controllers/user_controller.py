import uuid

from core.exceptions import UnauthorizedError
from models import User
from repositories import UserRepository


class UserController:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def get_authenticated_user(self, user_id: uuid.UUID | None) -> User:
        if user_id is None:
            raise UnauthorizedError("Não autenticado")
        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Usuário inválido ou inativo")
        return user
