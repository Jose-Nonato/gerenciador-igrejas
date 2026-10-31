from pydantic import BaseModel


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # Quando True o cliente deve levar o usuário direto à troca de senha
    troca_obrigatoria: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str
