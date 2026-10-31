import logging
from datetime import datetime, timedelta, timezone

from core import security
from core.config import settings
from core.exceptions import AppError
from core.mailer import Mailer
from models import Usuario
from models.enums import StatusUsuario
from repositories import (
    AuditoriaRepository,
    RefreshTokenRepository,
    TokenRedefinicaoRepository,
    UsuarioRepository,
)

logger = logging.getLogger(__name__)


class RedefinicaoSenhaController:
    """Convite de novo usuário e redefinição de senha: ambos usam o mesmo link de uso único."""

    def __init__(
        self,
        users: UsuarioRepository,
        resets: TokenRedefinicaoRepository,
        tokens: RefreshTokenRepository,
        audit: AuditoriaRepository,
        mailer: Mailer,
    ) -> None:
        self.users = users
        self.resets = resets
        self.tokens = tokens
        self.audit = audit
        self.mailer = mailer

    def solicitar(self, email: str) -> None:
        """Sempre retorna sem erro, exista o e-mail ou não (não revela cadastros)."""
        user = self.users.get_by_email(email.lower())
        if user is not None and user.status == StatusUsuario.ATIVO:
            self._enviar_link(
                user,
                "Redefinição de senha",
                "Recebemos um pedido para redefinir sua senha.",
            )

    def enviar_convite(self, user: Usuario) -> None:
        self._enviar_link(
            user,
            "Convite para o Gerenciador de Igrejas",
            "Você foi convidado(a). Defina sua senha para acessar o sistema.",
        )

    def redefinir(self, token: str, nova_senha: str) -> None:
        erro = AppError("Link inválido ou expirado")
        registro = self.resets.get_by_hash(security.hash_reset_token(token))
        if registro is None or registro.usado_em is not None:
            raise erro
        expira_em = registro.expira_em
        if expira_em.tzinfo is None:
            expira_em = expira_em.replace(tzinfo=timezone.utc)
        if expira_em < datetime.now(timezone.utc):
            raise erro

        user = self.users.get_by_id(registro.usuario_id)
        # Conta bloqueada/desativada não se recupera sozinha: precisa do administrador
        if user is None or user.status not in (StatusUsuario.ATIVO, StatusUsuario.CONVITE_PENDENTE):
            raise erro

        convite = user.status == StatusUsuario.CONVITE_PENDENTE
        self.users.update_password(
            user, security.hash_password(nova_senha), status=StatusUsuario.ATIVO
        )
        self.resets.mark_used(registro)
        self.tokens.revoke_all_for_user(user.id)
        self.audit.registrar(
            user.igreja_id, user.id,
            "convite_aceito" if convite else "senha_redefinida",
            "usuario", user.id,
        )

    def _enviar_link(self, user: Usuario, assunto: str, introducao: str) -> None:
        token = security.generate_reset_token()
        expira_em = datetime.now(timezone.utc) + timedelta(hours=settings.RESET_TOKEN_EXPIRE_HOURS)
        self.resets.create(user.igreja_id, user.id, security.hash_reset_token(token), expira_em)
        link = f"{settings.FRONTEND_URL.rstrip('/')}/redefinir-senha?token={token}"
        corpo = (
            f"{introducao}\n\n{link}\n\n"
            f"O link vale por {settings.RESET_TOKEN_EXPIRE_HOURS} horas e só pode ser usado uma vez."
        )
        try:
            self.mailer.enviar(user.email, assunto, corpo)
        except Exception:
            # Falha de e-mail não pode vazar nem derrubar a requisição; o admin pode reenviar
            logger.exception("Falha ao enviar e-mail para usuário %s", user.id)
