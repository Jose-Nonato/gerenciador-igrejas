import uuid
from datetime import datetime, timezone

import jwt

from core import security
from core.config import settings
from core.exceptions import ConflictError, UnauthorizedError
from models import Usuario
from models.enums import StatusUsuario
from repositories import AuditoriaRepository, RefreshTokenRepository, UsuarioRepository
from schemas import PasswordChange, TokenPair

# Hash fixo usado quando o e-mail não existe, para o tempo de resposta
# ser parecido e não revelar quais e-mails estão cadastrados.
_DUMMY_HASH = security.hash_password("dummy-password-for-timing")


class AuthController:
    def __init__(
        self,
        users: UsuarioRepository,
        tokens: RefreshTokenRepository,
        audit: AuditoriaRepository,
    ) -> None:
        self.users = users
        self.tokens = tokens
        self.audit = audit

    def login(self, email: str, password: str) -> TokenPair:
        user = self.users.get_by_email(email.lower())
        if user is None:
            security.verify_password(password, _DUMMY_HASH)
            raise UnauthorizedError("Credenciais inválidas")

        senha_ok = security.verify_password(password, user.senha_hash)
        # Mesma mensagem para bloqueado/desativado/convite pendente: não revela o estado da conta
        if user.status != StatusUsuario.ATIVO:
            raise UnauthorizedError("Credenciais inválidas")

        if not senha_ok:
            tentativas = self.users.register_failure(user)
            if tentativas >= settings.MAX_TENTATIVAS_LOGIN:
                self.users.set_status(user, StatusUsuario.BLOQUEADO)
                self.audit.registrar(
                    user.igreja_id, user.id, "login_bloqueado", "usuario", user.id,
                    {"tentativas": tentativas},
                )
            raise UnauthorizedError("Credenciais inválidas")

        self.users.register_success(user)
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = security.decode_token(refresh_token, expected_type="refresh")
            user_id = uuid.UUID(payload["sub"])
            jti = payload["jti"]
        except (jwt.InvalidTokenError, KeyError, ValueError):
            raise UnauthorizedError("Refresh token inválido")

        stored = self.tokens.get(jti)
        if stored is None or stored.usuario_id != user_id:
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
        if user is None or user.status != StatusUsuario.ATIVO:
            raise UnauthorizedError("Usuário inválido ou inativo")

        self.tokens.revoke(stored)
        return self._issue_tokens(user)

    def logout(self, user: Usuario) -> None:
        self.tokens.revoke_all_for_user(user.id)

    def change_password(self, user: Usuario, data: PasswordChange) -> None:
        if not security.verify_password(data.current_password, user.senha_hash):
            raise UnauthorizedError("Senha atual incorreta")
        if data.current_password == data.new_password:
            raise ConflictError("A nova senha deve ser diferente da atual")
        self.users.update_password(user, security.hash_password(data.new_password))
        # Encerra as outras sessões: refresh tokens antigos deixam de valer
        self.tokens.revoke_all_for_user(user.id)
        self.audit.registrar(user.igreja_id, user.id, "senha_alterada", "usuario", user.id)

    def _issue_tokens(self, user: Usuario) -> TokenPair:
        refresh, jti, expires_at = security.create_refresh_token(user.id)
        self.tokens.add(jti, user.id, expires_at)
        return TokenPair(
            access_token=security.create_access_token(user.id),
            refresh_token=refresh,
            troca_obrigatoria=user.troca_obrigatoria,
        )
