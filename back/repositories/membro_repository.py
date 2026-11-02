import uuid

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from models.enums import Oficio, Rol, SituacaoMembro
from models.evento_eclesiastico import EventoEclesiastico
from models.membro import Membro
from models.usuario import Usuario

# Os métodos de escrita deste módulo NÃO fazem commit: registrar um evento altera
# evento, membro e auditoria na mesma transação, e o commit fica com o controller.


class MembroRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_in_church(self, igreja_id: uuid.UUID, membro_id: uuid.UUID) -> Membro | None:
        return self.db.scalar(
            select(Membro).where(
                Membro.id == membro_id,
                Membro.igreja_id == igreja_id,
                Membro.excluido_em.is_(None),
            )
        )

    def search(
        self,
        igreja_id: uuid.UUID,
        *,
        q: str | None = None,
        rol: Rol | None = None,
        situacao: SituacaoMembro | None = None,
        oficio: Oficio | None = None,
        familia_id: uuid.UUID | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[Membro], int]:
        filtros = [Membro.igreja_id == igreja_id, Membro.excluido_em.is_(None)]
        if q:
            filtros.append(Membro.nome.icontains(q, autoescape=True))
        if rol:
            filtros.append(Membro.rol == rol)
        if situacao:
            filtros.append(Membro.situacao == situacao)
        if oficio:
            filtros.append(Membro.oficio == oficio)
        if familia_id:
            filtros.append(Membro.familia_id == familia_id)

        total = self.db.scalar(select(func.count()).select_from(Membro).where(*filtros)) or 0
        consulta = (
            select(Membro)
            .where(*filtros)
            .order_by(Membro.nome, Membro.id)
            .offset(offset)
        )
        if limit is not None:
            consulta = consulta.limit(limit)
        return list(self.db.scalars(consulta)), total

    def buscar_elegiveis(self, igreja_id: uuid.UUID, q: str, limit: int) -> list[Membro]:
        """Membros que ainda fazem parte do rol (ativos ou em disciplina), por parte do nome."""
        return list(
            self.db.scalars(
                select(Membro)
                .where(
                    Membro.igreja_id == igreja_id,
                    Membro.excluido_em.is_(None),
                    Membro.situacao.in_([SituacaoMembro.ATIVO, SituacaoMembro.EM_DISCIPLINA]),
                    Membro.nome.icontains(q, autoescape=True),
                )
                .order_by(Membro.nome, Membro.id)
                .limit(limit)
            )
        )

    def numero_rol_em_uso(
        self, igreja_id: uuid.UUID, numero: int, ignorar_id: uuid.UUID | None = None
    ) -> bool:
        consulta = select(Membro.id).where(
            Membro.igreja_id == igreja_id,
            Membro.numero_rol == numero,
            Membro.excluido_em.is_(None),
        )
        if ignorar_id:
            consulta = consulta.where(Membro.id != ignorar_id)
        return self.db.scalar(consulta) is not None

    def create(self, igreja_id: uuid.UUID, campos: dict, numero_rol: int | None) -> Membro:
        if numero_rol is None:
            # Serializa a geração do número por igreja até o fim da transação
            self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:chave))"),
                {"chave": f"numero_rol:{igreja_id}"},
            )
            maior = self.db.scalar(
                select(func.max(Membro.numero_rol)).where(
                    Membro.igreja_id == igreja_id, Membro.excluido_em.is_(None)
                )
            )
            numero_rol = (maior or 0) + 1
        membro = Membro(igreja_id=igreja_id, numero_rol=numero_rol, **campos)
        self.db.add(membro)
        self.db.flush()
        return membro

    def apply(self, membro: Membro, campos: dict) -> None:
        for chave, valor in campos.items():
            setattr(membro, chave, valor)
        self.db.flush()

    def excluir(self, membro: Membro) -> int:
        """Exclusão lógica. Desvincula a conta de usuário ligada ao membro e devolve
        quantas contas foram desvinculadas (0 ou 1)."""
        membro.excluido_em = func.now()
        desvinculadas = self.db.execute(
            update(Usuario).where(Usuario.membro_id == membro.id).values(membro_id=None)
        ).rowcount
        self.db.flush()
        return desvinculadas


class EventoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, igreja_id: uuid.UUID, membro_id: uuid.UUID, campos: dict) -> EventoEclesiastico:
        evento = EventoEclesiastico(igreja_id=igreja_id, membro_id=membro_id, **campos)
        self.db.add(evento)
        self.db.flush()
        return evento

    def list_by_membro(
        self, igreja_id: uuid.UUID, membro_id: uuid.UUID
    ) -> list[EventoEclesiastico]:
        return list(
            self.db.scalars(
                select(EventoEclesiastico)
                .where(
                    EventoEclesiastico.igreja_id == igreja_id,
                    EventoEclesiastico.membro_id == membro_id,
                )
                .order_by(EventoEclesiastico.data, EventoEclesiastico.id)
            )
        )
