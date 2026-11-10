import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from models.comunicado import Comunicado
from models.enums import StatusPost, TipoPublico
from models.membro import Membro
from models.sociedade import Sociedade
from models.usuario import Usuario

# Os métodos de escrita NÃO fazem commit: o commit (e a auditoria) ficam com o controller.


@dataclass(frozen=True)
class AudienciaLeitor:
    """A que públicos uma pessoa pertence. Decide o que ela lê no mural.

    `permite` (um comunicado em memória) e `condicao` (SQL das listagens) precisam dizer a
    mesma coisa. "professores_ebd" vale para quem é professor em exercício de uma classe
    ativa da EBD.
    """

    ve_tudo: bool = False
    comungante: bool = False
    oficial: bool = False
    professor_ebd: bool = False
    sociedades: frozenset[uuid.UUID] = field(default_factory=frozenset)

    def permite(self, publico: TipoPublico, sociedade_id: uuid.UUID | None) -> bool:
        if self.ve_tudo or publico == TipoPublico.IGREJA:
            return True
        if publico == TipoPublico.COMUNGANTES:
            return self.comungante
        if publico == TipoPublico.OFICIAIS:
            return self.oficial
        if publico == TipoPublico.PROFESSORES_EBD:
            return self.professor_ebd
        if publico == TipoPublico.SOCIEDADE:
            return sociedade_id in self.sociedades
        return False

    def condicao(self):
        if self.ve_tudo:
            return Comunicado.id.is_not(None)  # sempre verdadeiro
        opcoes = [Comunicado.publico == TipoPublico.IGREJA]
        if self.comungante:
            opcoes.append(Comunicado.publico == TipoPublico.COMUNGANTES)
        if self.oficial:
            opcoes.append(Comunicado.publico == TipoPublico.OFICIAIS)
        if self.professor_ebd:
            opcoes.append(Comunicado.publico == TipoPublico.PROFESSORES_EBD)
        if self.sociedades:
            opcoes.append(
                and_(
                    Comunicado.publico == TipoPublico.SOCIEDADE,
                    Comunicado.sociedade_id.in_(self.sociedades),
                )
            )
        return or_(*opcoes)


def esta_publicado(c: Comunicado, agora: datetime) -> bool:
    """Publicado, ou agendado cuja hora já chegou (não há tarefa em segundo plano)."""
    return c.status == StatusPost.PUBLICADO or (
        c.status == StatusPost.AGENDADO and c.publicar_em is not None and c.publicar_em <= agora
    )


def _publicado_sql(agora: datetime):
    return or_(
        Comunicado.status == StatusPost.PUBLICADO,
        and_(Comunicado.status == StatusPost.AGENDADO, Comunicado.publicar_em <= agora),
    )


Linha = tuple[Comunicado, str | None, str | None]  # comunicado, sigla da sociedade, autor

_AUTOR = func.coalesce(Membro.nome, Usuario.email)


class ComunicadoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base(self):
        return (
            select(Comunicado, Sociedade.sigla, _AUTOR)
            .outerjoin(Sociedade, Comunicado.sociedade_id == Sociedade.id)
            .outerjoin(Usuario, Comunicado.autor_id == Usuario.id)
            .outerjoin(Membro, Usuario.membro_id == Membro.id)
            .where(Comunicado.excluido_em.is_(None))
        )

    def get(self, igreja_id: uuid.UUID, comunicado_id: uuid.UUID) -> Linha | None:
        linha = self.db.execute(
            self._base().where(Comunicado.id == comunicado_id, Comunicado.igreja_id == igreja_id)
        ).first()
        return (linha[0], linha[1], linha[2]) if linha else None

    def create(self, igreja_id: uuid.UUID, campos: dict) -> Comunicado:
        comunicado = Comunicado(igreja_id=igreja_id, **campos)
        self.db.add(comunicado)
        self.db.flush()
        return comunicado

    def apply(self, comunicado: Comunicado, campos: dict) -> None:
        for chave, valor in campos.items():
            setattr(comunicado, chave, valor)
        self.db.flush()

    def _paginar(self, consulta, filtros: list, limit: int, offset: int) -> tuple[list[Linha], int]:
        total = (
            self.db.scalar(
                select(func.count()).select_from(Comunicado).where(Comunicado.excluido_em.is_(None), *filtros)
            )
            or 0
        )
        # Mais recente primeiro (rascunhos, sem data, pela criação)
        ordem = func.coalesce(Comunicado.publicado_em, Comunicado.publicar_em, Comunicado.criado_em)
        linhas = self.db.execute(
            consulta.where(*filtros).order_by(ordem.desc(), Comunicado.id).limit(limit).offset(offset)
        )
        return [(c, s, a) for c, s, a in linhas], total

    def mural(
        self, igreja_id: uuid.UUID, audiencia: AudienciaLeitor, agora: datetime,
        categoria=None, limit: int = 20, offset: int = 0,
    ) -> tuple[list[Linha], int]:
        """O que a pessoa lê: publicado e do público dela."""
        filtros = [Comunicado.igreja_id == igreja_id, _publicado_sql(agora), audiencia.condicao()]
        if categoria:
            filtros.append(Comunicado.categoria == categoria)
        return self._paginar(self._base(), filtros, limit, offset)

    def gerenciar(
        self, igreja_id: uuid.UUID, agora: datetime, sociedades: frozenset[uuid.UUID] | None,
        status: StatusPost | None = None, categoria=None, limit: int = 20, offset: int = 0,
    ) -> tuple[list[Linha], int]:
        """Para quem escreve. `sociedades` restringe aos comunicados dessas sociedades
        (líder); None = todos (admin e pastor)."""
        filtros = [Comunicado.igreja_id == igreja_id]
        if sociedades is not None:
            filtros += [
                Comunicado.publico == TipoPublico.SOCIEDADE,
                Comunicado.sociedade_id.in_(sociedades),
            ]
        if categoria:
            filtros.append(Comunicado.categoria == categoria)
        if status == StatusPost.PUBLICADO:
            filtros.append(_publicado_sql(agora))
        elif status == StatusPost.AGENDADO:
            filtros += [Comunicado.status == StatusPost.AGENDADO, Comunicado.publicar_em > agora]
        elif status == StatusPost.RASCUNHO:
            filtros.append(Comunicado.status == StatusPost.RASCUNHO)
        return self._paginar(self._base(), filtros, limit, offset)
