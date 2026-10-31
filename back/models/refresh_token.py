import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from models.usuario import Usuario


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="refresh_tokens")
