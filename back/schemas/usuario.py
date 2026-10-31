import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from models.enums import PerfilUsuario, StatusUsuario


class UsuarioCreate(BaseModel):
    email: EmailStr
    perfil: PerfilUsuario = PerfilUsuario.USUARIO


class UsuarioUpdate(BaseModel):
    """Alteração feita por um administrador em outro usuário."""

    email: EmailStr | None = None
    perfil: PerfilUsuario | None = None
    status: StatusUsuario | None = None
    # `null` explícito desvincula o membro; omitir o campo não mexe no vínculo
    membro_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _algum_campo(self):
        if (
            self.email is None
            and self.perfil is None
            and self.status is None
            and "membro_id" not in self.model_fields_set
        ):
            raise ValueError("Informe ao menos um campo: email, perfil, status ou membro_id")
        return self


class MeuPerfilUpdate(BaseModel):
    """Alteração que o próprio usuário faz nos seus dados; exige a senha atual."""

    email: EmailStr
    senha_atual: str = Field(max_length=128)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    igreja_id: uuid.UUID
    membro_id: uuid.UUID | None
    email: str
    perfil: PerfilUsuario
    status: StatusUsuario
    troca_obrigatoria: bool
    ultimo_acesso: datetime | None


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class EsqueciSenha(BaseModel):
    email: EmailStr


class RedefinirSenha(BaseModel):
    token: str = Field(max_length=256)
    nova_senha: str = Field(min_length=8, max_length=128)
