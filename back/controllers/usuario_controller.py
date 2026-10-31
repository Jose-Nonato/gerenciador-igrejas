import secrets
import uuid

from core import security
from core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from controllers.redefinicao_senha_controller import RedefinicaoSenhaController
from models import Usuario
from models.enums import StatusUsuario
from repositories import (
    AuditoriaRepository,
    MembroRepository,
    RefreshTokenRepository,
    UsuarioRepository,
)
from schemas import MeuPerfilUpdate, UsuarioCreate, UsuarioUpdate

# Estados que o administrador pode atribuir; convite_pendente só nasce da criação
_STATUS_ATRIBUIVEIS = {StatusUsuario.ATIVO, StatusUsuario.BLOQUEADO, StatusUsuario.DESATIVADO}


class UsuarioController:
    def __init__(
        self,
        users: UsuarioRepository,
        tokens: RefreshTokenRepository,
        audit: AuditoriaRepository,
        redefinicao: RedefinicaoSenhaController,
        membros: MembroRepository,
    ) -> None:
        self.users = users
        self.membros = membros
        self.tokens = tokens
        self.audit = audit
        self.redefinicao = redefinicao

    def get_authenticated_user(self, user_id: uuid.UUID | None) -> Usuario:
        if user_id is None:
            raise UnauthorizedError("Não autenticado")
        user = self.users.get_by_id(user_id)
        if user is None or user.status != StatusUsuario.ATIVO:
            raise UnauthorizedError("Usuário inválido ou inativo")
        return user

    def listar(self, ator: Usuario) -> list[Usuario]:
        return self.users.list_by_church(ator.igreja_id)

    def convidar(self, ator: Usuario, data: UsuarioCreate) -> Usuario:
        email = data.email.lower()
        if self.users.get_by_email(email):
            raise ConflictError("E-mail já cadastrado")
        # Senha aleatória descartada: o convidado define a própria pelo link do convite
        user = self.users.create(
            ator.igreja_id,
            email,
            security.hash_password(secrets.token_urlsafe(32)),
            perfil=data.perfil,
            status=StatusUsuario.CONVITE_PENDENTE,
        )
        self.audit.registrar(
            ator.igreja_id, ator.id, "usuario_criado", "usuario", user.id,
            {"email": email, "perfil": data.perfil.value},
        )
        self.redefinicao.enviar_convite(user)
        return user

    def reenviar_convite(self, ator: Usuario, usuario_id: uuid.UUID) -> None:
        user = self._get(ator, usuario_id)
        if user.status != StatusUsuario.CONVITE_PENDENTE:
            raise ConflictError("Usuário não está com convite pendente")
        self.redefinicao.enviar_convite(user)

    def atualizar(self, ator: Usuario, usuario_id: uuid.UUID, data: UsuarioUpdate) -> Usuario:
        user = self._get(ator, usuario_id)
        proprio = user.id == ator.id
        if proprio and (
            data.perfil is not None or data.status is not None or data.email is not None
        ):
            # E-mail próprio vai por PATCH /usuarios/me, que confere a senha atual
            raise ForbiddenError("Você não pode alterar o próprio perfil, status ou e-mail aqui")

        encerrar_sessoes = False
        if data.email is not None and self._trocar_email(ator, user, data.email):
            encerrar_sessoes = True
            if user.status == StatusUsuario.CONVITE_PENDENTE:
                # Novo link vai para o e-mail corrigido e invalida o enviado ao endereço antigo
                self.redefinicao.enviar_convite(user)

        if "membro_id" in data.model_fields_set:
            self._vincular_membro(ator, user, data.membro_id)

        if data.perfil is not None and data.perfil != user.perfil:
            antes = user.perfil.value
            self.users.set_perfil(user, data.perfil)
            self.audit.registrar(
                ator.igreja_id, ator.id, "perfil_alterado", "usuario", user.id,
                {"de": antes, "para": data.perfil.value},
            )
            encerrar_sessoes = True

        if data.status is not None and data.status != user.status:
            if data.status not in _STATUS_ATRIBUIVEIS:
                raise ConflictError("Status não pode ser atribuído manualmente")
            if user.status == StatusUsuario.CONVITE_PENDENTE:
                raise ConflictError("Usuário com convite pendente ainda não ativou a conta")
            antes = user.status.value
            self.users.set_status(user, data.status)
            self.audit.registrar(
                ator.igreja_id, ator.id, "status_alterado", "usuario", user.id,
                {"de": antes, "para": data.status.value},
            )
            encerrar_sessoes = encerrar_sessoes or data.status != StatusUsuario.ATIVO

        if encerrar_sessoes:
            self.tokens.revoke_all_for_user(user.id)
        return user

    def atualizar_me(self, user: Usuario, data: MeuPerfilUpdate) -> Usuario:
        if not security.verify_password(data.senha_atual, user.senha_hash):
            raise UnauthorizedError("Senha atual incorreta")
        if self._trocar_email(user, user, data.email):
            # Mesma regra da troca de senha: as sessões abertas deixam de valer
            self.tokens.revoke_all_for_user(user.id)
        return user

    def _vincular_membro(
        self, ator: Usuario, alvo: Usuario, membro_id: uuid.UUID | None
    ) -> None:
        if membro_id == alvo.membro_id:
            return
        if membro_id is not None:
            if self.membros.get_in_church(ator.igreja_id, membro_id) is None:
                raise NotFoundError("Membro não encontrado")
            outro = self.users.get_by_membro(membro_id)
            if outro is not None and outro.id != alvo.id:
                raise ConflictError("Este membro já está vinculado a outro usuário")
        antes = alvo.membro_id
        self.users.set_membro(alvo, membro_id)
        self.audit.registrar(
            ator.igreja_id, ator.id, "membro_vinculado", "usuario", alvo.id,
            {"de": str(antes) if antes else None, "para": str(membro_id) if membro_id else None},
        )

    def _trocar_email(self, ator: Usuario, alvo: Usuario, novo: str) -> bool:
        """Retorna True se o e-mail mudou. O e-mail é único no sistema todo."""
        novo = novo.lower()
        if novo == alvo.email:
            return False
        if self.users.get_by_email(novo):
            raise ConflictError("E-mail já cadastrado")
        antes = alvo.email
        self.users.set_email(alvo, novo)
        self.audit.registrar(
            ator.igreja_id, ator.id, "email_alterado", "usuario", alvo.id,
            {"de": antes, "para": novo},
        )
        return True

    def _get(self, ator: Usuario, usuario_id: uuid.UUID) -> Usuario:
        # Sempre filtrado pela igreja do ator: outra igreja aparece como inexistente
        user = self.users.get_in_church(ator.igreja_id, usuario_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        return user
