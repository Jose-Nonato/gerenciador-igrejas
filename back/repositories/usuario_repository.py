import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.enums import PerfilUsuario, StatusUsuario
from models.usuario import Usuario


class UsuarioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self.db.get(Usuario, usuario_id)

    def get_in_church(self, igreja_id: uuid.UUID, usuario_id: uuid.UUID) -> Usuario | None:
        return self.db.scalar(
            select(Usuario).where(Usuario.id == usuario_id, Usuario.igreja_id == igreja_id)
        )

    def get_by_email(self, email: str) -> Usuario | None:
        return self.db.scalar(select(Usuario).where(Usuario.email == email))

    def get_by_membro(self, membro_id: uuid.UUID) -> Usuario | None:
        return self.db.scalar(select(Usuario).where(Usuario.membro_id == membro_id))

    def set_membro(self, usuario: Usuario, membro_id: uuid.UUID | None) -> None:
        usuario.membro_id = membro_id
        self.db.commit()

    def list_by_church(self, igreja_id: uuid.UUID) -> list[Usuario]:
        return list(
            self.db.scalars(
                select(Usuario).where(Usuario.igreja_id == igreja_id).order_by(Usuario.email)
            )
        )

    def create(
        self,
        igreja_id: uuid.UUID,
        email: str,
        senha_hash: str,
        perfil: PerfilUsuario = PerfilUsuario.USUARIO,
        status: StatusUsuario = StatusUsuario.ATIVO,
        troca_obrigatoria: bool = False,
        membro_id: uuid.UUID | None = None,
    ) -> Usuario:
        usuario = Usuario(
            igreja_id=igreja_id,
            email=email,
            senha_hash=senha_hash,
            perfil=perfil,
            status=status,
            troca_obrigatoria=troca_obrigatoria,
            membro_id=membro_id,
        )
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def update_password(
        self, usuario: Usuario, senha_hash: str, status: StatusUsuario | None = None
    ) -> None:
        """Troca a senha e zera bloqueio por tentativas e a exigência de troca."""
        usuario.senha_hash = senha_hash
        usuario.troca_obrigatoria = False
        usuario.tentativas_falhas = 0
        if status is not None:
            usuario.status = status
        self.db.commit()

    def register_failure(self, usuario: Usuario) -> int:
        usuario.tentativas_falhas += 1
        self.db.commit()
        return usuario.tentativas_falhas

    def register_success(self, usuario: Usuario) -> None:
        usuario.tentativas_falhas = 0
        usuario.ultimo_acesso = datetime.now(timezone.utc)
        self.db.commit()

    def set_status(self, usuario: Usuario, status: StatusUsuario) -> None:
        usuario.status = status
        if status == StatusUsuario.ATIVO:
            usuario.tentativas_falhas = 0
        self.db.commit()

    def set_email(self, usuario: Usuario, email: str) -> None:
        usuario.email = email
        self.db.commit()

    def set_perfil(self, usuario: Usuario, perfil: PerfilUsuario) -> None:
        usuario.perfil = perfil
        self.db.commit()
