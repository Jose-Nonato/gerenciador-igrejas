import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.token_redefinicao import TokenRedefinicao


class TokenRedefinicaoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self, igreja_id: uuid.UUID, usuario_id: uuid.UUID, token_hash: str, expira_em: datetime
    ) -> TokenRedefinicao:
        # Um novo link invalida os anteriores ainda não usados
        self.db.execute(
            update(TokenRedefinicao)
            .where(TokenRedefinicao.usuario_id == usuario_id, TokenRedefinicao.usado_em.is_(None))
            .values(usado_em=datetime.now(timezone.utc))
        )
        token = TokenRedefinicao(
            igreja_id=igreja_id, usuario_id=usuario_id, token_hash=token_hash, expira_em=expira_em
        )
        self.db.add(token)
        self.db.commit()
        return token

    def get_by_hash(self, token_hash: str) -> TokenRedefinicao | None:
        return self.db.scalar(
            select(TokenRedefinicao).where(TokenRedefinicao.token_hash == token_hash)
        )

    def mark_used(self, token: TokenRedefinicao) -> None:
        token.usado_em = datetime.now(timezone.utc)
        self.db.commit()
