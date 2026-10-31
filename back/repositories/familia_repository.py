import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.familia import Familia


class FamiliaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_in_church(self, igreja_id: uuid.UUID, familia_id: uuid.UUID) -> Familia | None:
        return self.db.scalar(
            select(Familia).where(Familia.id == familia_id, Familia.igreja_id == igreja_id)
        )

    def list_by_church(self, igreja_id: uuid.UUID) -> list[Familia]:
        return list(
            self.db.scalars(
                select(Familia).where(Familia.igreja_id == igreja_id).order_by(Familia.nome)
            )
        )

    def create(self, igreja_id: uuid.UUID, nome: str, endereco: str | None) -> Familia:
        familia = Familia(igreja_id=igreja_id, nome=nome, endereco=endereco)
        self.db.add(familia)
        self.db.commit()
        self.db.refresh(familia)
        return familia

    def update(self, familia: Familia, campos: dict) -> Familia:
        for chave, valor in campos.items():
            setattr(familia, chave, valor)
        self.db.commit()
        self.db.refresh(familia)
        return familia

    def delete(self, familia: Familia) -> None:
        # membro.familia_id é SET NULL: os membros permanecem, apenas sem família
        self.db.delete(familia)
        self.db.commit()
