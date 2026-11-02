import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.enums import CargoLideranca, SiglaSociedade, StatusPresenca
from models.membro import Membro
from models.sociedade import Lideranca, Presenca, Reuniao, Socio, Sociedade

# Os métodos de escrita NÃO fazem commit: lançar presenças altera presença e auditoria na
# mesma transação, e o commit fica com o controller.

# Sócio cujo membro foi excluído (exclusão lógica) some das listagens
_MEMBRO_VIVO = or_(Socio.membro_id.is_(None), Membro.excluido_em.is_(None))
_NOME = func.coalesce(Membro.nome, Socio.nome_externo)


class SociedadeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- sociedade ----------

    def get(self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID) -> Sociedade | None:
        return self.db.scalar(
            select(Sociedade).where(
                Sociedade.id == sociedade_id, Sociedade.igreja_id == igreja_id
            )
        )

    def get_by_sigla(self, igreja_id: uuid.UUID, sigla: SiglaSociedade) -> Sociedade | None:
        return self.db.scalar(
            select(Sociedade).where(Sociedade.igreja_id == igreja_id, Sociedade.sigla == sigla)
        )

    def total_socios(self, sociedade_id: uuid.UUID) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Socio)
                .outerjoin(Membro, Socio.membro_id == Membro.id)
                .where(Socio.sociedade_id == sociedade_id, Socio.saiu_em.is_(None), _MEMBRO_VIVO)
            )
            or 0
        )

    def list_with_totals(
        self, igreja_id: uuid.UUID, ids: set[uuid.UUID] | None = None
    ) -> list[tuple[Sociedade, int]]:
        total = (
            select(func.count())
            .select_from(Socio)
            .outerjoin(Membro, Socio.membro_id == Membro.id)
            .where(Socio.sociedade_id == Sociedade.id, Socio.saiu_em.is_(None), _MEMBRO_VIVO)
            .correlate(Sociedade)
            .scalar_subquery()
        )
        consulta = select(Sociedade, total).where(Sociedade.igreja_id == igreja_id)
        if ids is not None:
            consulta = consulta.where(Sociedade.id.in_(ids))
        linhas = self.db.execute(consulta.order_by(Sociedade.sigla))
        return [(s, t) for s, t in linhas]

    def create(self, igreja_id: uuid.UUID, sigla: SiglaSociedade, nome: str | None) -> Sociedade:
        sociedade = Sociedade(igreja_id=igreja_id, sigla=sigla, nome=nome)
        self.db.add(sociedade)
        self.db.flush()
        return sociedade

    # ---------- sócios ----------

    def list_socios(
        self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID, incluir_ex: bool = False
    ) -> list[tuple[Socio, str]]:
        consulta = (
            select(Socio, _NOME)
            .outerjoin(Membro, Socio.membro_id == Membro.id)
            .where(Socio.igreja_id == igreja_id, Socio.sociedade_id == sociedade_id, _MEMBRO_VIVO)
            .order_by(_NOME, Socio.id)
        )
        if not incluir_ex:
            consulta = consulta.where(Socio.saiu_em.is_(None))
        return [(s, n) for s, n in self.db.execute(consulta)]

    def get_socio(
        self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID, socio_id: uuid.UUID
    ) -> tuple[Socio, str] | None:
        linha = self.db.execute(
            select(Socio, _NOME)
            .outerjoin(Membro, Socio.membro_id == Membro.id)
            .where(
                Socio.id == socio_id,
                Socio.igreja_id == igreja_id,
                Socio.sociedade_id == sociedade_id,
                _MEMBRO_VIVO,
            )
        ).first()
        return (linha[0], linha[1]) if linha else None

    def socio_ativo_do_membro(self, sociedade_id: uuid.UUID, membro_id: uuid.UUID) -> Socio | None:
        return self.db.scalar(
            select(Socio).where(
                Socio.sociedade_id == sociedade_id,
                Socio.membro_id == membro_id,
                Socio.saiu_em.is_(None),
            )
        )

    def create_socio(self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID, campos: dict) -> Socio:
        socio = Socio(igreja_id=igreja_id, sociedade_id=sociedade_id, **campos)
        self.db.add(socio)
        self.db.flush()
        self.db.refresh(socio)  # traz entrou_em (default do banco)
        return socio

    def apply(self, entidade, campos: dict) -> None:
        for chave, valor in campos.items():
            setattr(entidade, chave, valor)
        self.db.flush()

    # ---------- reuniões ----------

    def get_reuniao(
        self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID, reuniao_id: uuid.UUID
    ) -> Reuniao | None:
        return self.db.scalar(
            select(Reuniao).where(
                Reuniao.id == reuniao_id,
                Reuniao.igreja_id == igreja_id,
                Reuniao.sociedade_id == sociedade_id,
            )
        )

    def reuniao_na_data(
        self, sociedade_id: uuid.UUID, data: date, ignorar_id: uuid.UUID | None = None
    ) -> bool:
        consulta = select(Reuniao.id).where(
            Reuniao.sociedade_id == sociedade_id, Reuniao.data == data
        )
        if ignorar_id:
            consulta = consulta.where(Reuniao.id != ignorar_id)
        return self.db.scalar(consulta) is not None

    def create_reuniao(
        self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID, data: date, tema: str | None
    ) -> Reuniao:
        reuniao = Reuniao(igreja_id=igreja_id, sociedade_id=sociedade_id, data=data, tema=tema)
        self.db.add(reuniao)
        self.db.flush()
        return reuniao

    def _contagens(self):
        def conta(status: StatusPresenca):
            return func.count(Presenca.socio_id).filter(Presenca.status == status)

        return (
            conta(StatusPresenca.PRESENTE),
            conta(StatusPresenca.AUSENTE),
            conta(StatusPresenca.JUSTIFICADO),
        )

    def list_reunioes(
        self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID
    ) -> list[tuple[Reuniao, int, int, int]]:
        p, a, j = self._contagens()
        linhas = self.db.execute(
            select(Reuniao, p, a, j)
            .outerjoin(Presenca, Presenca.reuniao_id == Reuniao.id)
            .where(Reuniao.igreja_id == igreja_id, Reuniao.sociedade_id == sociedade_id)
            .group_by(Reuniao.id)
            .order_by(Reuniao.data.desc())
        )
        return [(r, *c) for r, *c in linhas]

    def contagem_da_reuniao(self, reuniao_id: uuid.UUID) -> tuple[int, int, int]:
        p, a, j = self._contagens()
        linha = self.db.execute(select(p, a, j).where(Presenca.reuniao_id == reuniao_id)).one()
        return (linha[0], linha[1], linha[2])

    # ---------- presença ----------

    def list_presencas(self, reuniao_id: uuid.UUID) -> list[tuple[Presenca, str]]:
        linhas = self.db.execute(
            select(Presenca, _NOME)
            .join(Socio, Socio.id == Presenca.socio_id)
            .outerjoin(Membro, Socio.membro_id == Membro.id)
            .where(Presenca.reuniao_id == reuniao_id)
            .order_by(_NOME, Socio.id)
        )
        return [(p, n) for p, n in linhas]

    def upsert_presencas(
        self, igreja_id: uuid.UUID, reuniao_id: uuid.UUID, itens: dict[uuid.UUID, StatusPresenca]
    ) -> None:
        existentes = {
            p.socio_id: p
            for p in self.db.scalars(select(Presenca).where(Presenca.reuniao_id == reuniao_id))
        }
        for socio_id, status in itens.items():
            if socio_id in existentes:
                existentes[socio_id].status = status
            else:
                self.db.add(
                    Presenca(
                        igreja_id=igreja_id, reuniao_id=reuniao_id, socio_id=socio_id, status=status
                    )
                )
        self.db.flush()

    # ---------- frequência ----------

    def total_reunioes(
        self, sociedade_id: uuid.UUID, de: date | None, ate: date | None
    ) -> int:
        consulta = select(func.count()).select_from(Reuniao).where(Reuniao.sociedade_id == sociedade_id)
        if de:
            consulta = consulta.where(Reuniao.data >= de)
        if ate:
            consulta = consulta.where(Reuniao.data <= ate)
        return self.db.scalar(consulta) or 0

    def contagem_por_socio(
        self, sociedade_id: uuid.UUID, de: date | None, ate: date | None
    ) -> dict[uuid.UUID, dict[StatusPresenca, int]]:
        consulta = (
            select(Presenca.socio_id, Presenca.status, func.count())
            .join(Reuniao, Reuniao.id == Presenca.reuniao_id)
            .where(Reuniao.sociedade_id == sociedade_id)
            .group_by(Presenca.socio_id, Presenca.status)
        )
        if de:
            consulta = consulta.where(Reuniao.data >= de)
        if ate:
            consulta = consulta.where(Reuniao.data <= ate)
        saida: dict[uuid.UUID, dict[StatusPresenca, int]] = {}
        for socio_id, status, n in self.db.execute(consulta):
            saida.setdefault(socio_id, {})[status] = n
        return saida


class LiderancaRepository:
    """Diretoria das sociedades. Sem commit nas escritas (o commit é do controller)."""

    # Líder cujo membro foi excluído (exclusão lógica) some das listagens
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base(self):
        return select(Lideranca, Membro.nome).join(Membro, Lideranca.membro_id == Membro.id).where(
            Membro.excluido_em.is_(None)
        )

    def list(
        self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID, incluir_encerrados: bool = False
    ) -> list[tuple[Lideranca, str]]:
        consulta = self._base().where(
            Lideranca.igreja_id == igreja_id, Lideranca.sociedade_id == sociedade_id
        )
        if not incluir_encerrados:
            consulta = consulta.where(Lideranca.fim.is_(None))
        # Em exercício primeiro, depois do mandato mais recente ao mais antigo
        consulta = consulta.order_by(
            Lideranca.fim.is_not(None), Lideranca.inicio.desc(), Membro.nome, Lideranca.id
        )
        return [(item, nome) for item, nome in self.db.execute(consulta)]

    def get(
        self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID, lideranca_id: uuid.UUID
    ) -> tuple[Lideranca, str] | None:
        linha = self.db.execute(
            self._base().where(
                Lideranca.id == lideranca_id,
                Lideranca.igreja_id == igreja_id,
                Lideranca.sociedade_id == sociedade_id,
            )
        ).first()
        return (linha[0], linha[1]) if linha else None

    def sociedades_lideradas(self, igreja_id: uuid.UUID, membro_id: uuid.UUID) -> set[uuid.UUID]:
        """Sociedades em que o membro tem um mandato em exercício (qualquer cargo)."""
        return set(
            self.db.scalars(
                select(Lideranca.sociedade_id).where(
                    Lideranca.igreja_id == igreja_id,
                    Lideranca.membro_id == membro_id,
                    Lideranca.fim.is_(None),
                )
            )
        )

    def ocupante_ativo(self, sociedade_id: uuid.UUID, cargo: CargoLideranca) -> Lideranca | None:
        return self.db.scalar(
            select(Lideranca).where(
                Lideranca.sociedade_id == sociedade_id,
                Lideranca.cargo == cargo,
                Lideranca.fim.is_(None),
            )
        )

    def membro_no_cargo(
        self, sociedade_id: uuid.UUID, membro_id: uuid.UUID, cargo: CargoLideranca,
        descricao: str | None,
    ) -> bool:
        consulta = select(Lideranca.id).where(
            Lideranca.sociedade_id == sociedade_id,
            Lideranca.membro_id == membro_id,
            Lideranca.cargo == cargo,
            Lideranca.fim.is_(None),
        )
        if descricao is not None:
            consulta = consulta.where(func.lower(Lideranca.cargo_descricao) == descricao.lower())
        return self.db.scalar(consulta) is not None

    def create(self, igreja_id: uuid.UUID, sociedade_id: uuid.UUID, campos: dict) -> Lideranca:
        item = Lideranca(igreja_id=igreja_id, sociedade_id=sociedade_id, **campos)
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)  # traz `inicio` (default do banco)
        return item

    def apply(self, item: Lideranca, campos: dict) -> None:
        for chave, valor in campos.items():
            setattr(item, chave, valor)
        self.db.flush()
