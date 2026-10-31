import uuid

from sqlalchemy.orm import Session

from models.igreja import Igreja


class IgrejaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, igreja_id: uuid.UUID) -> Igreja | None:
        return self.db.get(Igreja, igreja_id)

    def create(self, nome: str, **campos: str | None) -> Igreja:
        igreja = Igreja(nome=nome, **campos)
        self.db.add(igreja)
        self.db.commit()
        self.db.refresh(igreja)
        return igreja

    def update(self, igreja: Igreja, campos: dict) -> Igreja:
        for chave, valor in campos.items():
            setattr(igreja, chave, valor)
        self.db.commit()
        self.db.refresh(igreja)
        return igreja
