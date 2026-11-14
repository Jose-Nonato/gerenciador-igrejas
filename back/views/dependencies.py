from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from controllers import (
    AtendimentoController,
    AuthController,
    ComunicadoController,
    EbdController,
    FamiliaController,
    IgrejaController,
    MembroController,
    RedefinicaoSenhaController,
    SociedadeController,
    UsuarioController,
)
from core.database import get_db
from core.exceptions import ForbiddenError
from core.mailer import Mailer, get_mailer
from models import Usuario
from models.enums import PerfilUsuario
from repositories import (
    AtendimentoRepository,
    AuditoriaRepository,
    ComunicadoRepository,
    EbdRepository,
    EventoRepository,
    FamiliaRepository,
    IgrejaRepository,
    MembroRepository,
    LiderancaRepository,
    RefreshTokenRepository,
    SociedadeRepository,
    TokenRedefinicaoRepository,
    UsuarioRepository,
)

DbSession = Annotated[Session, Depends(get_db)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]


def get_auth_controller(db: DbSession) -> AuthController:
    return AuthController(UsuarioRepository(db), RefreshTokenRepository(db), AuditoriaRepository(db))


def get_redefinicao_controller(db: DbSession, mailer: MailerDep) -> RedefinicaoSenhaController:
    return RedefinicaoSenhaController(
        UsuarioRepository(db),
        TokenRedefinicaoRepository(db),
        RefreshTokenRepository(db),
        AuditoriaRepository(db),
        mailer,
    )


def get_usuario_controller(
    db: DbSession,
    redefinicao: Annotated[RedefinicaoSenhaController, Depends(get_redefinicao_controller)],
) -> UsuarioController:
    return UsuarioController(
        UsuarioRepository(db),
        RefreshTokenRepository(db),
        AuditoriaRepository(db),
        redefinicao,
        MembroRepository(db),
    )


def get_igreja_controller(db: DbSession) -> IgrejaController:
    return IgrejaController(IgrejaRepository(db))


def get_familia_controller(db: DbSession) -> FamiliaController:
    return FamiliaController(FamiliaRepository(db))


def get_membro_controller(db: DbSession) -> MembroController:
    return MembroController(
        MembroRepository(db),
        FamiliaRepository(db),
        EventoRepository(db),
        AuditoriaRepository(db),
        db,
    )


def get_sociedade_controller(db: DbSession) -> SociedadeController:
    return SociedadeController(
        SociedadeRepository(db),
        MembroRepository(db),
        AuditoriaRepository(db),
        db,
        LiderancaRepository(db),
    )


def get_ebd_controller(db: DbSession) -> EbdController:
    return EbdController(EbdRepository(db), MembroRepository(db), AuditoriaRepository(db), db)


def get_atendimento_controller(db: DbSession, mailer: MailerDep) -> AtendimentoController:
    return AtendimentoController(
        AtendimentoRepository(db), MembroRepository(db), AuditoriaRepository(db), db, mailer
    )


def get_comunicado_controller(db: DbSession) -> ComunicadoController:
    return ComunicadoController(
        ComunicadoRepository(db),
        SociedadeRepository(db),
        LiderancaRepository(db),
        MembroRepository(db),
        AuditoriaRepository(db),
        db,
        EbdRepository(db),
    )


# Só documenta o esquema Bearer no OpenAPI (botão "Authorize" no /docs);
# a validação do token continua sendo feita pelo JWTAuthMiddleware.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    controller: Annotated[UsuarioController, Depends(get_usuario_controller)],
    _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> Usuario:
    return controller.get_authenticated_user(getattr(request.state, "user_id", None))


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def get_active_user(user: CurrentUser) -> Usuario:
    """Igual a CurrentUser, mas bloqueia quem ainda precisa trocar a senha."""
    if user.troca_obrigatoria:
        raise ForbiddenError("Troca de senha obrigatória")
    return user


ActiveUser = Annotated[Usuario, Depends(get_active_user)]


def require_perfil(*perfis: PerfilUsuario):
    def checker(user: ActiveUser) -> Usuario:
        if user.perfil not in perfis:
            raise ForbiddenError("Sem permissão para esta operação")
        return user

    return checker


AdminUser = Annotated[Usuario, Depends(require_perfil(PerfilUsuario.ADMIN))]
StaffUser = Annotated[
    Usuario,
    Depends(require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.PASTOR, PerfilUsuario.PRESBITERO)),
]

# Ações destrutivas no rol: só quem responde pela igreja
GestorUser = Annotated[Usuario, Depends(require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.PASTOR))]

AuthCtrl = Annotated[AuthController, Depends(get_auth_controller)]
RedefinicaoCtrl = Annotated[RedefinicaoSenhaController, Depends(get_redefinicao_controller)]
UsuarioCtrl = Annotated[UsuarioController, Depends(get_usuario_controller)]
IgrejaCtrl = Annotated[IgrejaController, Depends(get_igreja_controller)]
FamiliaCtrl = Annotated[FamiliaController, Depends(get_familia_controller)]
MembroCtrl = Annotated[MembroController, Depends(get_membro_controller)]
SociedadeCtrl = Annotated[SociedadeController, Depends(get_sociedade_controller)]
EbdCtrl = Annotated[EbdController, Depends(get_ebd_controller)]
AtendimentoCtrl = Annotated[AtendimentoController, Depends(get_atendimento_controller)]
ComunicadoCtrl = Annotated[ComunicadoController, Depends(get_comunicado_controller)]
