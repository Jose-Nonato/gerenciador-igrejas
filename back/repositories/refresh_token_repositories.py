import uuid
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, jti: str) -> RefreshToken | None:
        return self.db.get(RefreshToken, jti)

    def add(self, jti: str, usuario_id: uuid.UUID, expires_at: datetime) -> None:
        self.db.add(RefreshToken(jti=jti, usuario_id=usuario_id, expires_at=expires_at))
        self.db.commit()

    def revoke(self, token: RefreshToken) -> None:
        token.revoked = True
        self.db.commit()

    def revoke_all_for_user(self, usuario_id: uuid.UUID) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.usuario_id == usuario_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        self.db.commit()
