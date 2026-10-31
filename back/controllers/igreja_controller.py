from core.exceptions import NotFoundError
from models import Igreja, Usuario
from repositories import IgrejaRepository
from schemas import IgrejaUpdate


class IgrejaController:
    def __init__(self, igrejas: IgrejaRepository) -> None:
        self.igrejas = igrejas

    def get(self, ator: Usuario) -> Igreja:
        igreja = self.igrejas.get(ator.igreja_id)
        if igreja is None:
            raise NotFoundError("Igreja não encontrada")
        return igreja

    def update(self, ator: Usuario, data: IgrejaUpdate) -> Igreja:
        igreja = self.get(ator)
        campos = data.model_dump(exclude_unset=True)
        if campos.get("nome") is None:
            campos.pop("nome", None)  # nome é obrigatório; null explícito é ignorado
        return self.igrejas.update(igreja, campos)
