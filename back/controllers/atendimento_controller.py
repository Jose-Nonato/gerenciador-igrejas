import logging
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import settings
from core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from core.mailer import Mailer
from models import Usuario
from models.atendimento import Atendimento, DisponibilidadeAtendimento
from models.enums import ModalidadeAtendimento, PerfilUsuario, SituacaoMembro, StatusAtendimento
from repositories import AtendimentoRepository, AuditoriaRepository, MembroRepository
from schemas import (
    AtendimentoCreate,
    BloqueioCreate,
    DisponibilidadeCreate,
    DisponibilidadeUpdate,
    RemarcacaoIn,
)

_OFICIAIS = (PerfilUsuario.PASTOR, PerfilUsuario.PRESBITERO)
_FORA_DO_ROL = {SituacaoMembro.TRANSFERIDO, SituacaoMembro.FALECIDO, SituacaoMembro.EXCLUIDO}
_UTC = timezone.utc
_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MODALIDADE = {"presencial": "presencial", "online": "online", "visita": "visita"}

logger = logging.getLogger(__name__)


def _agora() -> datetime:
    return datetime.now(_UTC)


def _minutos(t: time) -> int:
    return t.hour * 60 + t.minute


class AtendimentoController:
    """Agendamento de conversas com pastor e presbíteros.

    O membro pede um horário de um oficial; o oficial confirma ou recusa. Só o solicitante e
    o oficial do atendimento o enxergam (inclusive o assunto): para qualquer outro usuário,
    admin inclusive, ele não existe. A auditoria guarda o fato e a mudança de status, nunca o
    assunto nem a justificativa.

    Os horários marcáveis não ficam gravados: saem das janelas semanais do oficial, fatiadas
    pela duração, menos o que já foi reservado e o que está fora da antecedência mínima e do
    horizonte.
    """

    def __init__(
        self,
        atendimentos: AtendimentoRepository,
        membros: MembroRepository,
        audit: AuditoriaRepository,
        db: Session,
        mailer: Mailer,
    ) -> None:
        self.atendimentos = atendimentos
        self.membros = membros
        self.audit = audit
        self.db = db
        self.mailer = mailer
        self.tz = ZoneInfo(settings.FUSO_HORARIO)

    # ---------- acesso ----------

    @staticmethod
    def _e_oficial(ator: Usuario) -> bool:
        return ator.perfil in _OFICIAIS

    def _exigir_oficial(self, ator: Usuario) -> None:
        if not self._e_oficial(ator):
            raise ForbiddenError("Apenas pastor e presbíteros têm agenda de atendimentos")

    def _commit(self, mensagem_conflito: str) -> None:
        try:
            self.db.commit()
        except IntegrityError:
            # Corrida entre duas requisições: a restrição única do banco decide
            self.db.rollback()
            raise ConflictError(mensagem_conflito)

    # ---------- disponibilidade (só o próprio oficial) ----------

    def _sobrepoe(
        self,
        ator: Usuario,
        dia: int,
        inicio: time,
        fim: time,
        ignorar_id: uuid.UUID | None = None,
    ) -> bool:
        for outra in self.atendimentos.list_disponibilidades(
            ator.igreja_id, ator.id, so_ativas=True
        ):
            if outra.id == ignorar_id or outra.dia_semana != dia:
                continue
            if outra.hora_inicio < fim and inicio < outra.hora_fim:
                return True
        return False

    def listar_disponibilidades(self, ator: Usuario) -> list[DisponibilidadeAtendimento]:
        self._exigir_oficial(ator)
        return self.atendimentos.list_disponibilidades(ator.igreja_id, ator.id)

    def criar_disponibilidade(
        self, ator: Usuario, data: DisponibilidadeCreate
    ) -> DisponibilidadeAtendimento:
        self._exigir_oficial(ator)
        if self._sobrepoe(ator, data.dia_semana, data.hora_inicio, data.hora_fim):
            raise ConflictError("Esta janela se sobrepõe a outra já cadastrada no mesmo dia")
        disp = self.atendimentos.create_disponibilidade(
            ator.igreja_id, ator.id, data.model_dump()
        )
        self.audit.registrar(
            ator.igreja_id, ator.id, "disponibilidade_criada", "disponibilidade_atendimento",
            disp.id, {"dia_semana": disp.dia_semana}, commit=False,
        )
        self.db.commit()
        return disp

    def _disponibilidade(self, ator: Usuario, disp_id: uuid.UUID) -> DisponibilidadeAtendimento:
        self._exigir_oficial(ator)
        disp = self.atendimentos.get_disponibilidade(ator.igreja_id, ator.id, disp_id)
        if disp is None:
            raise NotFoundError("Janela não encontrada")
        return disp

    def atualizar_disponibilidade(
        self, ator: Usuario, disp_id: uuid.UUID, data: DisponibilidadeUpdate
    ) -> DisponibilidadeAtendimento:
        disp = self._disponibilidade(ator, disp_id)
        campos = data.model_dump(exclude_unset=True)
        dia = campos.get("dia_semana", disp.dia_semana)
        inicio = campos.get("hora_inicio", disp.hora_inicio)
        fim = campos.get("hora_fim", disp.hora_fim)
        duracao = campos.get("duracao_min", disp.duracao_min)
        ativa = campos.get("ativa", disp.ativa)
        if _minutos(fim) <= _minutos(inicio):
            raise AppError("O fim deve ser depois do início")
        if _minutos(fim) - _minutos(inicio) < duracao:
            raise AppError("A janela é menor que a duração do atendimento")
        if ativa and self._sobrepoe(ator, dia, inicio, fim, ignorar_id=disp.id):
            raise ConflictError("Esta janela se sobrepõe a outra já cadastrada no mesmo dia")
        self.atendimentos.apply(disp, campos)
        self.audit.registrar(
            ator.igreja_id, ator.id, "disponibilidade_alterada", "disponibilidade_atendimento",
            disp.id, {"campos": sorted(campos)}, commit=False,
        )
        self.db.commit()
        return disp

    def remover_disponibilidade(self, ator: Usuario, disp_id: uuid.UUID) -> None:
        disp = self._disponibilidade(ator, disp_id)
        self.atendimentos.delete_disponibilidade(disp)
        self.audit.registrar(
            ator.igreja_id, ator.id, "disponibilidade_removida", "disponibilidade_atendimento",
            disp_id, None, commit=False,
        )
        self.db.commit()

    # ---------- oficiais e horários livres ----------

    def listar_oficiais(self, ator: Usuario) -> list[tuple[Usuario, str]]:
        return self.atendimentos.list_oficiais_com_agenda(ator.igreja_id, ator.id)

    def _horarios(
        self, oficial: Usuario, de: date, ate: date
    ) -> list[tuple[datetime, datetime, DisponibilidadeAtendimento]]:
        """Horários livres do oficial entre as datas (do relógio da igreja), já descontados a
        antecedência mínima, o horizonte e o que está reservado."""
        agora = _agora()
        minimo = agora + timedelta(hours=settings.ATENDIMENTO_ANTECEDENCIA_HORAS)
        maximo = agora + timedelta(days=settings.ATENDIMENTO_HORIZONTE_DIAS)

        por_dia: dict[int, list[DisponibilidadeAtendimento]] = defaultdict(list)
        for d in self.atendimentos.list_disponibilidades(
            oficial.igreja_id, oficial.id, so_ativas=True
        ):
            por_dia[d.dia_semana].append(d)

        bloqueios = self.atendimentos.bloqueios_no_periodo(oficial.id, de, ate)
        candidatos: list[tuple[datetime, datetime, DisponibilidadeAtendimento]] = []
        dia = de
        while dia <= ate:
            janelas = [] if self._bloqueado(bloqueios, dia) else por_dia.get(dia.weekday(), [])
            for d in janelas:
                # Aritmética no relógio local (naive) e só depois o fuso: janela de 19h às 21h
                # continua sendo 19h às 21h mesmo na troca de horário de verão
                cursor = datetime.combine(dia, d.hora_inicio)
                limite = datetime.combine(dia, d.hora_fim)
                passo = timedelta(minutes=d.duracao_min)
                while cursor + passo <= limite:
                    ini = cursor.replace(tzinfo=self.tz).astimezone(_UTC)
                    fim = (cursor + passo).replace(tzinfo=self.tz).astimezone(_UTC)
                    if minimo <= ini <= maximo:
                        candidatos.append((ini, fim, d))
                    cursor += passo
            dia += timedelta(days=1)

        if not candidatos:
            return []
        ocupados = self.atendimentos.ocupados(
            oficial.id, min(c[0] for c in candidatos), max(c[0] for c in candidatos) + timedelta(seconds=1)
        )
        livres = [c for c in candidatos if c[0] not in ocupados]
        return sorted(livres, key=lambda c: c[0])

    def _oficial(self, ator: Usuario, oficial_id: uuid.UUID) -> Usuario:
        oficial = self.atendimentos.get_oficial(ator.igreja_id, oficial_id)
        if oficial is None:
            raise NotFoundError("Oficial não encontrado")
        if oficial.id == ator.id:
            raise AppError("Você não pode agendar uma conversa consigo mesmo")
        return oficial

    def _listar_horarios(self, oficial: Usuario, de: date | None, ate: date | None) -> list[dict]:
        hoje = _agora().astimezone(self.tz).date()
        de = de or hoje
        ate = ate or de + timedelta(days=14)
        if ate < de:
            raise AppError("A data final não pode ser antes da inicial")
        if (ate - de).days > settings.ATENDIMENTO_HORIZONTE_DIAS:
            raise AppError(
                f"Consulte no máximo {settings.ATENDIMENTO_HORIZONTE_DIAS} dias por vez"
            )
        return [
            {
                "inicio": ini.astimezone(self.tz),
                "fim": fim.astimezone(self.tz),
                "modalidade": d.modalidade,
                "local": d.local,
            }
            for ini, fim, d in self._horarios(oficial, de, ate)
        ]

    def horarios_livres(
        self, ator: Usuario, oficial_id: uuid.UUID, de: date | None, ate: date | None
    ) -> list[dict]:
        return self._listar_horarios(self._oficial(ator, oficial_id), de, ate)

    def horarios_proprios(self, ator: Usuario, de: date | None, ate: date | None) -> list[dict]:
        """Os horários livres da própria agenda: o oficial escolhe um para propor uma remarcação."""
        self._exigir_oficial(ator)
        return self._listar_horarios(ator, de, ate)

    @staticmethod
    def _bloqueado(bloqueios: list, dia: date) -> bool:
        return any(b.de <= dia <= b.ate for b in bloqueios)

    # ---------- atendimentos ----------

    def _dados(self, achado: tuple[Atendimento, str, str]) -> dict:
        a, solicitante_nome, oficial_nome = achado
        return {
            "id": a.id,
            "solicitante_id": a.solicitante_id,
            "solicitante_nome": solicitante_nome,
            "oficial_id": a.oficial_id,
            "oficial_nome": oficial_nome,
            "inicio": a.inicio,
            "fim": a.fim,
            "modalidade": a.modalidade,
            "local": a.local,
            "status": a.status,
            "categoria": a.categoria,
            "assunto": a.assunto,
            "justificativa": a.justificativa,
            "proposta_inicio": a.proposta_inicio,
            "proposta_fim": a.proposta_fim,
            "proposta_modalidade": a.proposta_modalidade,
            "proposta_local": a.proposta_local,
            "criado_em": a.criado_em,
        }

    def _e_parte(self, ator: Usuario, a: Atendimento) -> bool:
        return a.oficial_id == ator.id or (
            ator.membro_id is not None and a.solicitante_id == ator.membro_id
        )

    def get(self, ator: Usuario, atendimento_id: uuid.UUID) -> dict:
        achado = self.atendimentos.get(ator.igreja_id, atendimento_id)
        # Quem não é parte recebe 404, como se o atendimento não existisse
        if achado is None or not self._e_parte(ator, achado[0]):
            raise NotFoundError("Atendimento não encontrado")
        return self._dados(achado)

    def listar_meus(self, ator: Usuario, status: StatusAtendimento | None) -> list[dict]:
        if ator.membro_id is None:
            return []
        achados = self.atendimentos.listar(
            ator.igreja_id, solicitante_id=ator.membro_id, status=status
        )
        return [self._dados(a) for a in achados]

    def listar_recebidos(self, ator: Usuario, status: StatusAtendimento | None) -> list[dict]:
        self._exigir_oficial(ator)
        achados = self.atendimentos.listar(ator.igreja_id, oficial_id=ator.id, status=status)
        return [self._dados(a) for a in achados]

    def solicitar(self, ator: Usuario, data: AtendimentoCreate) -> dict:
        if ator.membro_id is None:
            raise ForbiddenError("Sua conta não está vinculada a um membro")
        membro = self.membros.get_in_church(ator.igreja_id, ator.membro_id)
        if membro is None or membro.situacao in _FORA_DO_ROL:
            raise ConflictError("Você não faz mais parte do rol de membros")
        oficial = self._oficial(ator, data.oficial_id)

        inicio = data.inicio.astimezone(_UTC)
        dia = inicio.astimezone(self.tz).date()
        slot = next((s for s in self._horarios(oficial, dia, dia) if s[0] == inicio), None)
        if slot is None:
            raise ConflictError("Este horário não está disponível")
        _, fim, janela = slot

        agora = _agora()
        if self.atendimentos.pendentes_futuros(membro.id, agora) >= settings.ATENDIMENTO_MAX_PENDENTES:
            raise ConflictError(
                f"Você já tem {settings.ATENDIMENTO_MAX_PENDENTES} pedidos aguardando resposta"
            )
        if self.atendimentos.conflito_do_solicitante(membro.id, inicio, fim):
            raise ConflictError("Você já tem outra conversa marcada neste horário")

        atendimento = self.atendimentos.create(
            ator.igreja_id,
            {
                "solicitante_id": membro.id,
                "oficial_id": oficial.id,
                "inicio": inicio,
                "fim": fim,
                "modalidade": janela.modalidade,
                "local": janela.local,
                "status": StatusAtendimento.SOLICITADO,
                "categoria": data.categoria,
                "assunto": data.assunto,
            },
        )
        self._auditar(ator, "atendimento_solicitado", atendimento)
        self._commit("Este horário acabou de ser reservado por outra pessoa")
        dados = self.get(ator, atendimento.id)
        self._avisar(atendimento, "oficial", "solicitado")
        return dados

    # ---------- respostas e andamento ----------

    def _auditar(self, ator: Usuario, acao: str, a: Atendimento) -> None:
        # Sem assunto nem justificativa: são sigilosos
        self.audit.registrar(
            ator.igreja_id, ator.id, acao, "atendimento", a.id,
            {
                "oficial_id": str(a.oficial_id),
                "solicitante_id": str(a.solicitante_id),
                "inicio": a.inicio.isoformat(),
            },
            commit=False,
        )

    def _carregar(self, ator: Usuario, atendimento_id: uuid.UUID) -> tuple[Atendimento, bool]:
        """Atendimento travado para alteração e se o ator é o oficial dele."""
        a = self.atendimentos.get_para_atualizar(ator.igreja_id, atendimento_id)
        if a is None or not self._e_parte(ator, a):
            raise NotFoundError("Atendimento não encontrado")
        return a, a.oficial_id == ator.id

    def _mudar(
        self,
        ator: Usuario,
        a: Atendimento,
        novo: StatusAtendimento,
        justificativa: str | None = None,
        avisar: str | None = None,
    ) -> dict:
        campos: dict = {"status": novo}
        if justificativa is not None:
            campos["justificativa"] = justificativa
        if a.status == StatusAtendimento.REMARCACAO:
            # Sai da remarcação (recusada ou retirada): a proposta deixa de valer
            campos.update(
                proposta_inicio=None, proposta_fim=None, proposta_modalidade=None, proposta_local=None
            )
        self.atendimentos.apply(a, campos)
        self._auditar(ator, f"atendimento_{novo.value}", a)
        self.db.commit()
        dados = self.get(ator, a.id)
        if avisar:
            self._avisar(a, avisar, novo.value)
        return dados

    def confirmar(self, ator: Usuario, atendimento_id: uuid.UUID) -> dict:
        a, e_oficial = self._carregar(ator, atendimento_id)
        if not e_oficial:
            raise ForbiddenError("Só o oficial pode confirmar")
        if a.status != StatusAtendimento.SOLICITADO:
            raise ConflictError("Este pedido já foi respondido")
        if a.inicio <= _agora():
            raise ConflictError("O horário deste pedido já passou")
        return self._mudar(ator, a, StatusAtendimento.CONFIRMADO, avisar="solicitante")

    def recusar(self, ator: Usuario, atendimento_id: uuid.UUID, justificativa: str | None) -> dict:
        a, e_oficial = self._carregar(ator, atendimento_id)
        if not e_oficial:
            raise ForbiddenError("Só o oficial pode recusar")
        if a.status != StatusAtendimento.SOLICITADO:
            raise ConflictError("Este pedido já foi respondido")
        return self._mudar(ator, a, StatusAtendimento.RECUSADO, justificativa, avisar="solicitante")

    def cancelar(self, ator: Usuario, atendimento_id: uuid.UUID, justificativa: str | None) -> dict:
        a, e_oficial = self._carregar(ator, atendimento_id)
        agora = _agora()
        if a.status == StatusAtendimento.SOLICITADO:
            if e_oficial:
                raise AppError("Para um pedido aguardando resposta, use Recusar")
        elif a.status == StatusAtendimento.CONFIRMADO:
            if a.inicio <= agora:
                raise ConflictError("Este horário já passou")
            limite = timedelta(hours=settings.ATENDIMENTO_CANCELAMENTO_HORAS)
            if not e_oficial and a.inicio - agora < limite:
                raise ConflictError(
                    f"Só é possível cancelar com {settings.ATENDIMENTO_CANCELAMENTO_HORAS} horas "
                    "de antecedência. Fale com o oficial"
                )
        elif a.status == StatusAtendimento.REMARCACAO:
            # Quem pediu a conversa recusa o novo horário; o oficial retira a proposta
            pass
        else:
            raise ConflictError("Este atendimento não pode mais ser cancelado")
        # Avisa a outra parte: quem cancelou já sabe
        outra = "solicitante" if e_oficial else "oficial"
        return self._mudar(ator, a, StatusAtendimento.CANCELADO, justificativa, avisar=outra)

    def _encerrar(
        self, ator: Usuario, atendimento_id: uuid.UUID, novo: StatusAtendimento
    ) -> dict:
        a, e_oficial = self._carregar(ator, atendimento_id)
        if not e_oficial:
            raise ForbiddenError("Só o oficial pode registrar isso")
        if a.status != StatusAtendimento.CONFIRMADO:
            raise ConflictError("Só é possível registrar um atendimento confirmado")
        if a.inicio > _agora():
            raise ConflictError("Só é possível registrar depois do horário marcado")
        return self._mudar(ator, a, novo)

    def concluir(self, ator: Usuario, atendimento_id: uuid.UUID) -> dict:
        return self._encerrar(ator, atendimento_id, StatusAtendimento.REALIZADO)

    def faltou(self, ator: Usuario, atendimento_id: uuid.UUID) -> dict:
        return self._encerrar(ator, atendimento_id, StatusAtendimento.FALTOU)

    # ---------- e-mails ----------
    #
    # Os e-mails dizem quem, quando e onde, e mandam abrir o sistema. Nunca levam o assunto
    # nem o motivo de uma recusa ou cancelamento: e-mail é menos reservado que o sistema.

    def _quando(self, inicio: datetime) -> str:
        local = inicio.astimezone(self.tz)
        return f"{_SEMANA[local.weekday()]}, {local:%d/%m/%Y}, às {local:%H:%M}"

    @staticmethod
    def _descrever_onde(modalidade: str, local: str | None) -> str:
        texto = _MODALIDADE[modalidade]
        return f"{texto} ({local})" if local else texto

    def _onde(self, a: Atendimento) -> str:
        return self._descrever_onde(a.modalidade.value, a.local)

    def _link(self, aba: str) -> str:
        return f"{settings.FRONTEND_URL.rstrip('/')}/agenda?aba={aba}"

    def _destinatario(self, a: Atendimento, quem: str) -> str | None:
        """E-mail de `quem` ("oficial" ou "solicitante"), se houver conta ativa."""
        if quem == "oficial":
            oficial = self.atendimentos.get_usuario(a.igreja_id, a.oficial_id)
            return oficial.email if oficial else None
        conta = self.atendimentos.usuario_do_membro(a.igreja_id, a.solicitante_id)
        return conta.email if conta else None

    def _enviar(self, destinatario: str, assunto: str, corpo: str) -> bool:
        try:
            self.mailer.enviar(destinatario, assunto, corpo)
            return True
        except Exception:
            # Falha de e-mail não derruba a requisição nem desfaz o atendimento
            logger.exception("Falha ao enviar e-mail de atendimento")
            return False

    def _avisar(self, a: Atendimento, quem: str, evento: str) -> None:
        achado = self.atendimentos.get(a.igreja_id, a.id)
        destino = self._destinatario(a, quem)
        if achado is None or destino is None:
            return
        _, nome_solicitante, nome_oficial = achado
        quando = self._quando(a.inicio)
        onde = self._onde(a)
        if evento == "solicitado":
            assunto = f"Novo pedido de conversa: {nome_solicitante}"
            corpo = (
                f"{nome_solicitante} pediu uma conversa com você em {quando} ({onde}).\n\n"
                f"Confirme ou recuse em {self._link('recebidos')}"
            )
        elif evento == "confirmado":
            assunto = "Sua conversa foi confirmada"
            corpo = (
                f"{nome_oficial} confirmou a conversa de {quando} ({onde}).\n\n"
                f"Detalhes em {self._link('meus')}"
            )
        elif evento == "recusado":
            assunto = "Seu pedido de conversa não pôde ser atendido"
            corpo = (
                f"{nome_oficial} não poderá atender o pedido de {quando}.\n\n"
                f"Veja o motivo e escolha outro horário em {self._link('meus')}"
            )
        elif evento == "remarcacao":
            assunto = "Novo horário proposto para a sua conversa"
            novo = self._quando(a.proposta_inicio)
            novo_onde = self._descrever_onde(a.proposta_modalidade, a.proposta_local)
            corpo = (
                f"{nome_oficial} propôs {novo} ({novo_onde}) no lugar de {quando}.\n\n"
                f"Aceite ou recuse em {self._link('meus')}"
            )
        elif evento == "remarcacao_aceita":
            assunto = "Novo horário aceito"
            corpo = (
                f"{nome_solicitante} aceitou o novo horário: {quando} ({onde}).\n\n"
                f"Detalhes em {self._link('recebidos')}"
            )
        else:  # cancelado
            assunto = "Conversa cancelada"
            corpo = (
                f"A conversa de {quando} entre {nome_solicitante} e {nome_oficial} foi cancelada.\n\n"
                f"Detalhes em {self._link('recebidos' if quem == 'oficial' else 'meus')}"
            )
        self._enviar(destino, assunto, corpo)

    def enviar_lembretes(self, agora: datetime | None = None) -> int:
        """Lembra por e-mail (solicitante e oficial) das conversas confirmadas que começam nas
        próximas ATENDIMENTO_LEMBRETE_HORAS horas. Roda fora de uma requisição (cron ou Agendador
        de Tarefas). Cada atendimento é lembrado uma vez. Devolve quantos foram lembrados."""
        agora = agora or _agora()
        ate = agora + timedelta(hours=settings.ATENDIMENTO_LEMBRETE_HORAS)
        lembrados = 0
        for a in self.atendimentos.lembretes_devidos(agora, ate):
            achado = self.atendimentos.get(a.igreja_id, a.id)
            if achado is None:
                continue
            _, nome_solicitante, nome_oficial = achado
            quando = self._quando(a.inicio)
            onde = self._onde(a)
            enviados = 0
            for quem, outro, aba in (
                ("solicitante", nome_oficial, "meus"),
                ("oficial", nome_solicitante, "recebidos"),
            ):
                destino = self._destinatario(a, quem)
                if destino is None:
                    continue
                corpo = (
                    f"Lembrete: você tem uma conversa com {outro} em {quando} ({onde}).\n\n"
                    f"Detalhes em {self._link(aba)}"
                )
                if self._enviar(destino, "Lembrete de conversa", corpo):
                    enviados += 1
            # Só marca se ao menos um e-mail saiu: se tudo falhou, a próxima rodada tenta de novo
            if enviados:
                a.lembrete_enviado_em = agora
                lembrados += 1
        self.db.commit()
        return lembrados

    # ---------- remarcação ----------

    def remarcar(self, ator: Usuario, atendimento_id: uuid.UUID, data: RemarcacaoIn) -> dict:
        """O oficial propõe outro horário (livre na agenda dele) para uma conversa pendente ou
        confirmada. Nada muda de fato até quem pediu a conversa aceitar."""
        a, e_oficial = self._carregar(ator, atendimento_id)
        if not e_oficial:
            raise ForbiddenError("Só o oficial pode propor outro horário")
        if a.status not in (StatusAtendimento.SOLICITADO, StatusAtendimento.CONFIRMADO):
            raise ConflictError("Só dá para remarcar uma conversa pendente ou confirmada")
        if a.inicio <= _agora():
            raise ConflictError("O horário desta conversa já passou")

        novo = data.inicio.astimezone(_UTC)
        dia = novo.astimezone(self.tz).date()
        slot = next((s for s in self._horarios(ator, dia, dia) if s[0] == novo), None)
        if slot is None:
            raise ConflictError("Este horário não está disponível")
        _, fim, janela = slot
        if self.atendimentos.conflito_do_solicitante(a.solicitante_id, novo, fim, ignorar_id=a.id):
            raise ConflictError("Quem pediu a conversa já tem outra marcada nesse horário")

        self.atendimentos.apply(
            a,
            {
                "status": StatusAtendimento.REMARCACAO,
                "proposta_inicio": novo,
                "proposta_fim": fim,
                "proposta_modalidade": janela.modalidade.value,
                "proposta_local": janela.local,
            },
        )
        self._auditar(ator, "atendimento_remarcacao_proposta", a)
        self.db.commit()
        dados = self.get(ator, a.id)
        self._avisar(a, "solicitante", "remarcacao")
        return dados

    def aceitar_remarcacao(self, ator: Usuario, atendimento_id: uuid.UUID) -> dict:
        """Quem pediu a conversa aceita o novo horário: a conversa passa a ser nele, confirmada.
        Recusar o novo horário é cancelar a conversa (`cancelar`)."""
        a, e_oficial = self._carregar(ator, atendimento_id)
        if e_oficial:
            raise ForbiddenError("Só quem pediu a conversa pode aceitar o novo horário")
        if a.status != StatusAtendimento.REMARCACAO:
            raise ConflictError("Não há novo horário esperando a sua resposta")
        if a.proposta_inicio <= _agora():
            raise ConflictError("O horário proposto já passou. Peça outro ao oficial")
        dia = a.proposta_inicio.astimezone(self.tz).date()
        if self.atendimentos.bloqueios_no_periodo(a.oficial_id, dia, dia):
            raise ConflictError("O oficial não atende nessa data. Peça outro horário")
        if self.atendimentos.conflito_do_solicitante(
            a.solicitante_id, a.proposta_inicio, a.proposta_fim, ignorar_id=a.id
        ):
            raise ConflictError("Você já tem outra conversa marcada neste horário")

        try:
            self.atendimentos.apply(
                a,
                {
                    "inicio": a.proposta_inicio,
                    "fim": a.proposta_fim,
                    "modalidade": ModalidadeAtendimento(a.proposta_modalidade),
                    "local": a.proposta_local,
                    "status": StatusAtendimento.CONFIRMADO,
                    "proposta_inicio": None,
                    "proposta_fim": None,
                    "proposta_modalidade": None,
                    "proposta_local": None,
                    # O horário mudou: o lembrete vale para o novo
                    "lembrete_enviado_em": None,
                },
            )
            self._auditar(ator, "atendimento_remarcacao_aceita", a)
            self.db.commit()
        except IntegrityError:
            # Outra conversa ocupou o horário (a restrição única do banco decide)
            self.db.rollback()
            raise ConflictError("Este horário acabou de ser reservado por outra pessoa")
        dados = self.get(ator, a.id)
        self._avisar(a, "oficial", "remarcacao_aceita")
        return dados

    # ---------- bloqueios de agenda (só o próprio oficial) ----------

    def _hoje(self) -> date:
        return _agora().astimezone(self.tz).date()

    def _bloqueio_dados(self, b) -> dict:
        inicio = datetime.combine(b.de, time.min).replace(tzinfo=self.tz).astimezone(_UTC)
        fim = (
            datetime.combine(b.ate + timedelta(days=1), time.min)
            .replace(tzinfo=self.tz)
            .astimezone(_UTC)
        )
        return {
            "id": b.id,
            "de": b.de,
            "ate": b.ate,
            "motivo": b.motivo,
            "atendimentos_afetados": self.atendimentos.contar_ativos_no_periodo(
                b.oficial_id, inicio, fim
            ),
        }

    def listar_bloqueios(self, ator: Usuario) -> list[dict]:
        """Bloqueios em curso ou futuros (os que já acabaram não interessam mais)."""
        self._exigir_oficial(ator)
        return [
            self._bloqueio_dados(b)
            for b in self.atendimentos.list_bloqueios(
                ator.igreja_id, ator.id, a_partir_de=self._hoje()
            )
        ]

    def criar_bloqueio(self, ator: Usuario, data: BloqueioCreate) -> dict:
        self._exigir_oficial(ator)
        if data.ate < self._hoje():
            raise AppError("Este período já passou")
        bloqueio = self.atendimentos.create_bloqueio(ator.igreja_id, ator.id, data.model_dump())
        self.audit.registrar(
            ator.igreja_id, ator.id, "bloqueio_agenda_criado", "bloqueio_agenda", bloqueio.id,
            {"de": data.de.isoformat(), "ate": data.ate.isoformat()}, commit=False,
        )
        self.db.commit()
        return self._bloqueio_dados(bloqueio)

    def remover_bloqueio(self, ator: Usuario, bloqueio_id: uuid.UUID) -> None:
        self._exigir_oficial(ator)
        bloqueio = self.atendimentos.get_bloqueio(ator.igreja_id, ator.id, bloqueio_id)
        if bloqueio is None:
            raise NotFoundError("Bloqueio não encontrado")
        self.atendimentos.delete_bloqueio(bloqueio)
        self.audit.registrar(
            ator.igreja_id, ator.id, "bloqueio_agenda_removido", "bloqueio_agenda", bloqueio_id,
            None, commit=False,
        )
        self.db.commit()

    # ---------- relatório (só do próprio oficial) ----------

    def relatorio(self, ator: Usuario, de: date | None, ate: date | None) -> list[dict]:
        """Conversas do oficial por mês e situação. Só números: nada que identifique alguém, nem
        o assunto. Cada oficial vê apenas o próprio relatório."""
        self._exigir_oficial(ator)
        if ate is None:
            # Até o fim do mês corrente: as conversas já marcadas para os próximos dias entram
            # como "em andamento"
            hoje = self._hoje()
            ate = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if de is None:
            total = ate.year * 12 + (ate.month - 1) - 11
            de = date(total // 12, total % 12 + 1, 1)
        if de > ate:
            raise AppError("A data final não pode ser antes da inicial")
        quantidade = (ate.year * 12 + ate.month) - (de.year * 12 + de.month) + 1
        if quantidade > 24:
            raise AppError("Consulte no máximo 24 meses por vez")

        inicio = datetime.combine(de, time.min).replace(tzinfo=self.tz).astimezone(_UTC)
        fim = (
            datetime.combine(ate + timedelta(days=1), time.min)
            .replace(tzinfo=self.tz)
            .astimezone(_UTC)
        )
        meses: dict[str, dict] = {}
        for i in range(quantidade):
            n = de.year * 12 + (de.month - 1) + i
            chave = f"{n // 12:04d}-{n % 12 + 1:02d}"
            meses[chave] = {
                "mes": chave, "total": 0, "realizados": 0, "faltas": 0,
                "cancelados": 0, "recusados": 0, "em_andamento": 0,
            }
        coluna = {
            StatusAtendimento.REALIZADO: "realizados",
            StatusAtendimento.FALTOU: "faltas",
            StatusAtendimento.CANCELADO: "cancelados",
            StatusAtendimento.RECUSADO: "recusados",
        }
        for inicio_a, status in self.atendimentos.inicios_e_status(ator.id, inicio, fim):
            local = inicio_a.astimezone(self.tz)
            linha = meses.get(f"{local.year:04d}-{local.month:02d}")
            if linha is None:
                continue
            linha["total"] += 1
            linha[coluna.get(status, "em_andamento")] += 1
        return list(meses.values())
