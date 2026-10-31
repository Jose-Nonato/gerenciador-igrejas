import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPk:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class IgrejaScoped:
    """Toda tabela, exceto `igreja`, pertence a uma igreja (multi-igreja)."""

    igreja_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("igreja.id", ondelete="RESTRICT"), index=True
    )
