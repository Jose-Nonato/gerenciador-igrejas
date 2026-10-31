import uuid

from sqlalchemy.orm import Session

from models.log_auditoria import LogAuditoria


class AuditoriaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def registrar(
        self,
        igreja_id: uuid.UUID,
        usuario_id: uuid.UUID | None,
        acao: str,
        entidade: str,
        entidade_id: uuid.UUID | None = None,
        detalhes: dict | None = None,
        commit: bool = True,
    ) -> None:
        self.db.add(
            LogAuditoria(
                igreja_id=igreja_id,
                usuario_id=usuario_id,
                acao=acao,
                entidade=entidade,
                entidade_id=entidade_id,
                detalhes=detalhes,
            )
        )
        if commit:
            self.db.commit()
