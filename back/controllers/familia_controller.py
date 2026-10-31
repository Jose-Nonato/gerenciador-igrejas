import uuid

from core.exceptions import NotFoundError
from models import Familia, Usuario
from repositories import FamiliaRepository
from schemas import FamiliaCreate, FamiliaUpdate


class FamiliaController:
    def __init__(self, familias: FamiliaRepository) -> None:
        self.familias = familias

    def listar(self, ator: Usuario) -> list[Familia]:
        return self.familias.list_by_church(ator.igreja_id)

    def get(self, ator: Usuario, familia_id: uuid.UUID) -> Familia:
        familia = self.familias.get_in_church(ator.igreja_id, familia_id)
        if familia is None:
            raise NotFoundError("Família não encontrada")
        return familia

    def criar(self, ator: Usuario, data: FamiliaCreate) -> Familia:
        return self.familias.create(ator.igreja_id, data.nome, data.endereco)

    def atualizar(self, ator: Usuario, familia_id: uuid.UUID, data: FamiliaUpdate) -> Familia:
        familia = self.get(ator, familia_id)
        campos = data.model_dump(exclude_unset=True)
        if campos.get("nome") is None:
            campos.pop("nome", None)  # nome é obrigatório
        return self.familias.update(familia, campos)

    def excluir(self, ator: Usuario, familia_id: uuid.UUID) -> None:
        self.familias.delete(self.get(ator, familia_id))
