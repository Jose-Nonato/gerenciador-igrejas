import uuid
from datetime import datetime, timezone

import jwt

from core import security
from core.exceptions import ConflictError, UnauthorizedError
from models import User
from repositories import RefreshTokenRepository, UserRepository
from schemas import PasswordChange, TokenPair, UserCreate

# Hash fixo usado quando o e-mail não existe, para o tempo de resposta
# ser parecido e não revelar quais e-mails estão cadastrados.
_DUMMY_HASH = security.hash_password("dummy-password-for-timing")


class AuthController:
    def __init__(self, users: UserRepository, tokens: RefreshTokenRepository) -> None:
        self.users = users
        self.tokens = tokens

    def register(self, data: UserCreate) -> User:
        email = data.email.lower()
        if self.users.get_by_email(email):
            raise ConflictError("E-mail já cadastrado")
        return self.users.create(email, security.hash_password(data.password))

    def login(self, email: str, password: str) -> TokenPair:
        user = self.users.get_by_email(email.lower())
        if user is None:
            security.verify_password(password, _DUMMY_HASH)
            raise UnauthorizedError("Credenciais inválidas")
        if not security.verify_password(password, user.hashed_password) or not user.is_active:
            raise UnauthorizedError("Credenciais inválidas")
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = security.decode_token(refresh_token, expected_type="refresh")
            user_id = uuid.UUID(payload["sub"])
            jti = payload["jti"]
        except (jwt.InvalidTokenError, KeyError, ValueError):
            raise UnauthorizedError("Refresh token inválido")

        stored = self.tokens.get(jti)
        if stored is None or stored.user_id != user_id:
            raise UnauthorizedError("Refresh token inválido")

        if stored.revoked:
            self.tokens.revoke_all_for_user(user_id)
            raise UnauthorizedError("Refresh token reutilizado")

        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError("Refresh token expirado")

        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Usuário inválido ou inativo")

        self.tokens.revoke(stored)
        return self._issue_tokens(user)

    def logout(self, user: User) -> None:
        self.tokens.revoke_all_for_user(user.id)

    def change_password(self, user: User, data: PasswordChange) -> None:
        if not security.verify_password(data.current_password, user.hashed_password):
            raise UnauthorizedError("Senha atual incorreta")
        if data.current_password == data.new_password:
            raise ConflictError("A nova senha deve ser diferente da atual")
        self.users.update_password(user, security.hash_password(data.new_password))
        # Encerra as outras sessões: refresh tokens antigos deixam de valer
        self.tokens.revoke_all_for_user(user.id)

    def _issue_tokens(self, user: User) -> TokenPair:
        refresh, jti, expires_at = security.create_refresh_token(user.id)
        self.tokens.add(jti, user.id, expires_at)
        return TokenPair(access_token=security.create_access_token(user.id), refresh_token=refresh)
