import uuid
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from models.atendimento import Atendimento, BloqueioAgenda, DisponibilidadeAtendimento
from models.enums import PerfilUsuario, StatusAtendimento, StatusUsuario
from models.membro import Membro
from models.usuario import Usuario

ATIVOS = (StatusAtendimento.SOLICITADO, StatusAtendimento.CONFIRMADO)
OFICIAIS = (PerfilUsuario.PASTOR, PerfilUsuario.PRESBITERO)

# Os métodos de escrita NÃO fazem commit: o commit fica com o controller, junto da auditoria.


class AtendimentoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def apply(self, entidade, campos: dict) -> None:
        for chave, valor in campos.items():
            setattr(entidade, chave, valor)
        self.db.flush()

    # ---------- disponibilidade ----------

    def get_disponibilidade(
        self, igreja_id: uuid.UUID, oficial_id: uuid.UUID, disp_id: uuid.UUID
    ) -> DisponibilidadeAtendimento | None:
        d = DisponibilidadeAtendimento
        return self.db.scalar(
            select(d).where(d.id == disp_id, d.igreja_id == igreja_id, d.oficial_id == oficial_id)
        )

    def list_disponibilidades(
        self, igreja_id: uuid.UUID, oficial_id: uuid.UUID, so_ativas: bool = False
    ) -> list[DisponibilidadeAtendimento]:
        d = DisponibilidadeAtendimento
        consulta = select(d).where(d.igreja_id == igreja_id, d.oficial_id == oficial_id)
        if so_ativas:
            consulta = consulta.where(d.ativa.is_(True))
        return list(self.db.scalars(consulta.order_by(d.dia_semana, d.hora_inicio)))

    def create_disponibilidade(
        self, igreja_id: uuid.UUID, oficial_id: uuid.UUID, campos: dict
    ) -> DisponibilidadeAtendimento:
        disp = DisponibilidadeAtendimento(igreja_id=igreja_id, oficial_id=oficial_id, **campos)
        self.db.add(disp)
        self.db.flush()
        return disp

    def delete_disponibilidade(self, disp: DisponibilidadeAtendimento) -> None:
        self.db.delete(disp)
        self.db.flush()

    # ---------- oficiais ----------

    def get_oficial(self, igreja_id: uuid.UUID, usuario_id: uuid.UUID) -> Usuario | None:
        return self.db.scalar(
            select(Usuario).where(
                Usuario.id == usuario_id,
                Usuario.igreja_id == igreja_id,
                Usuario.perfil.in_(OFICIAIS),
                Usuario.status == StatusUsuario.ATIVO,
            )
        )

    def list_oficiais_com_agenda(
        self, igreja_id: uuid.UUID, excluir_id: uuid.UUID
    ) -> list[tuple[Usuario, str]]:
        """Oficiais ativos com ao menos uma janela ativa, com o nome (do membro, ou o e-mail)."""
        d = DisponibilidadeAtendimento
        tem_agenda = select(d.id).where(d.oficial_id == Usuario.id, d.ativa.is_(True)).exists()
        nome = func.coalesce(Membro.nome, Usuario.email)
        consulta = (
            select(Usuario, nome)
            .outerjoin(Membro, Usuario.membro_id == Membro.id)
            .where(
                Usuario.igreja_id == igreja_id,
                Usuario.perfil.in_(OFICIAIS),
                Usuario.status == StatusUsuario.ATIVO,
                Usuario.id != excluir_id,
                tem_agenda,
            )
            .order_by(nome)
        )
        return [(u, n) for u, n in self.db.execute(consulta)]

    # ---------- atendimentos ----------

    @staticmethod
    def _com_nomes():
        oficial_membro = aliased(Membro)
        oficial = aliased(Usuario)
        return (
            select(Atendimento, Membro.nome, func.coalesce(oficial_membro.nome, oficial.email))
            .join(Membro, Atendimento.solicitante_id == Membro.id)
            .join(oficial, Atendimento.oficial_id == oficial.id)
            .outerjoin(oficial_membro, oficial.membro_id == oficial_membro.id)
        )

    def get(
        self, igreja_id: uuid.UUID, atendimento_id: uuid.UUID
    ) -> tuple[Atendimento, str, str] | None:
        linha = self.db.execute(
            self._com_nomes().where(
                Atendimento.id == atendimento_id, Atendimento.igreja_id == igreja_id
            )
        ).first()
        return (linha[0], linha[1], linha[2]) if linha else None

    def get_para_atualizar(
        self, igreja_id: uuid.UUID, atendimento_id: uuid.UUID
    ) -> Atendimento | None:
        """Trava a linha: duas respostas simultâneas ao mesmo atendimento não se atropelam."""
        return self.db.scalar(
            select(Atendimento)
            .where(Atendimento.id == atendimento_id, Atendimento.igreja_id == igreja_id)
            .with_for_update()
        )

    def listar(
        self,
        igreja_id: uuid.UUID,
        *,
        solicitante_id: uuid.UUID | None = None,
        oficial_id: uuid.UUID | None = None,
        status: StatusAtendimento | None = None,
        limite: int = 200,
    ) -> list[tuple[Atendimento, str, str]]:
        consulta = self._com_nomes().where(Atendimento.igreja_id == igreja_id)
        if solicitante_id is not None:
            consulta = consulta.where(Atendimento.solicitante_id == solicitante_id)
        if oficial_id is not None:
            consulta = consulta.where(Atendimento.oficial_id == oficial_id)
        if status is not None:
            consulta = consulta.where(Atendimento.status == status)
        consulta = consulta.order_by(Atendimento.inicio.desc(), Atendimento.id).limit(limite)
        return [(a, s, o) for a, s, o in self.db.execute(consulta)]

    def ocupados(self, oficial_id: uuid.UUID, de: datetime, ate: datetime) -> set[datetime]:
        """Inícios já reservados de um oficial no período: conversas solicitadas ou confirmadas,
        mais os horários propostos numa remarcação em aberto (ficam guardados para quem vai
        responder)."""
        reservados = set(
            self.db.scalars(
                select(Atendimento.inicio).where(
                    Atendimento.oficial_id == oficial_id,
                    Atendimento.status.in_(ATIVOS),
                    Atendimento.inicio >= de,
                    Atendimento.inicio < ate,
                )
            )
        )
        reservados.update(
            self.db.scalars(
                select(Atendimento.proposta_inicio).where(
                    Atendimento.oficial_id == oficial_id,
                    Atendimento.status == StatusAtendimento.REMARCACAO,
                    Atendimento.proposta_inicio >= de,
                    Atendimento.proposta_inicio < ate,
                )
            )
        )
        return reservados

    def pendentes_futuros(self, solicitante_id: uuid.UUID, agora: datetime) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Atendimento)
                .where(
                    Atendimento.solicitante_id == solicitante_id,
                    Atendimento.status == StatusAtendimento.SOLICITADO,
                    Atendimento.inicio > agora,
                )
            )
            or 0
        )

    def conflito_do_solicitante(
        self,
        solicitante_id: uuid.UUID,
        inicio: datetime,
        fim: datetime,
        ignorar_id: uuid.UUID | None = None,
    ) -> bool:
        """O membro já tem outra conversa (ativa) que se sobrepõe a este horário?"""
        consulta = select(Atendimento.id).where(
            Atendimento.solicitante_id == solicitante_id,
            Atendimento.status.in_(ATIVOS),
            Atendimento.inicio < fim,
            Atendimento.fim > inicio,
        )
        if ignorar_id is not None:
            consulta = consulta.where(Atendimento.id != ignorar_id)
        return self.db.scalar(consulta.limit(1)) is not None

    def usuario_do_membro(self, igreja_id: uuid.UUID, membro_id: uuid.UUID) -> Usuario | None:
        """Conta ativa ligada ao membro (é para ela que vai o e-mail)."""
        return self.db.scalar(
            select(Usuario).where(
                Usuario.igreja_id == igreja_id,
                Usuario.membro_id == membro_id,
                Usuario.status == StatusUsuario.ATIVO,
            )
        )

    def get_usuario(self, igreja_id: uuid.UUID, usuario_id: uuid.UUID) -> Usuario | None:
        return self.db.scalar(
            select(Usuario).where(Usuario.id == usuario_id, Usuario.igreja_id == igreja_id)
        )

    def lembretes_devidos(self, agora: datetime, ate: datetime) -> list[Atendimento]:
        """Confirmados que começam até `ate` e ainda não foram lembrados. Trava as linhas e
        pula as já travadas: dois disparos simultâneos do script não lembram duas vezes."""
        return list(
            self.db.scalars(
                select(Atendimento)
                .where(
                    Atendimento.status == StatusAtendimento.CONFIRMADO,
                    Atendimento.lembrete_enviado_em.is_(None),
                    Atendimento.inicio > agora,
                    Atendimento.inicio <= ate,
                )
                .order_by(Atendimento.inicio)
                .with_for_update(skip_locked=True)
            )
        )

    def create(self, igreja_id: uuid.UUID, campos: dict) -> Atendimento:
        atendimento = Atendimento(igreja_id=igreja_id, **campos)
        self.db.add(atendimento)
        self.db.flush()
        return atendimento

    # ---------- bloqueios de agenda ----------

    def list_bloqueios(
        self, igreja_id: uuid.UUID, oficial_id: uuid.UUID, a_partir_de: date | None = None
    ) -> list[BloqueioAgenda]:
        b = BloqueioAgenda
        consulta = select(b).where(b.igreja_id == igreja_id, b.oficial_id == oficial_id)
        if a_partir_de is not None:
            consulta = consulta.where(b.ate >= a_partir_de)
        return list(self.db.scalars(consulta.order_by(b.de, b.ate)))

    def bloqueios_no_periodo(
        self, oficial_id: uuid.UUID, de: date, ate: date
    ) -> list[BloqueioAgenda]:
        b = BloqueioAgenda
        return list(
            self.db.scalars(select(b).where(b.oficial_id == oficial_id, b.de <= ate, b.ate >= de))
        )

    def get_bloqueio(
        self, igreja_id: uuid.UUID, oficial_id: uuid.UUID, bloqueio_id: uuid.UUID
    ) -> BloqueioAgenda | None:
        b = BloqueioAgenda
        return self.db.scalar(
            select(b).where(b.id == bloqueio_id, b.igreja_id == igreja_id, b.oficial_id == oficial_id)
        )

    def create_bloqueio(
        self, igreja_id: uuid.UUID, oficial_id: uuid.UUID, campos: dict
    ) -> BloqueioAgenda:
        bloqueio = BloqueioAgenda(igreja_id=igreja_id, oficial_id=oficial_id, **campos)
        self.db.add(bloqueio)
        self.db.flush()
        return bloqueio

    def delete_bloqueio(self, bloqueio: BloqueioAgenda) -> None:
        self.db.delete(bloqueio)
        self.db.flush()

    def contar_ativos_no_periodo(
        self, oficial_id: uuid.UUID, inicio: datetime, fim: datetime
    ) -> int:
        """Conversas ainda em aberto (pendentes, confirmadas ou com remarcação esperando
        resposta) do oficial que começam no período."""
        ativos = (*ATIVOS, StatusAtendimento.REMARCACAO)
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Atendimento)
                .where(
                    Atendimento.oficial_id == oficial_id,
                    Atendimento.status.in_(ativos),
                    or_(
                        (Atendimento.inicio >= inicio) & (Atendimento.inicio < fim),
                        (Atendimento.proposta_inicio >= inicio) & (Atendimento.proposta_inicio < fim),
                    ),
                )
            )
            or 0
        )

    # ---------- relatório ----------

    def inicios_e_status(
        self, oficial_id: uuid.UUID, de: datetime, ate: datetime
    ) -> list[tuple[datetime, StatusAtendimento]]:
        return [
            (i, s)
            for i, s in self.db.execute(
                select(Atendimento.inicio, Atendimento.status).where(
                    Atendimento.oficial_id == oficial_id,
                    Atendimento.inicio >= de,
                    Atendimento.inicio < ate,
                )
            )
        ]
