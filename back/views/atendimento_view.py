import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from models import Usuario
from models.atendimento import DisponibilidadeAtendimento
from models.enums import StatusAtendimento
from schemas import (
    AtendimentoCreate,
    AtendimentoOut,
    BloqueioCreate,
    BloqueioOut,
    DisponibilidadeCreate,
    DisponibilidadeOut,
    DisponibilidadeUpdate,
    HorarioOut,
    JustificativaIn,
    OficialOut,
    RelatorioMesOut,
    RemarcacaoIn,
)
from views.dependencies import ActiveUser, AtendimentoCtrl

# Agendamento de conversas com pastor e presbíteros. Qualquer membro com conta pede um
# horário; só o pastor e os presbíteros têm agenda. Cada atendimento é visível apenas para
# o solicitante e o oficial (a regra está em AtendimentoController).
router = APIRouter(prefix="/agenda", tags=["agenda"])


def _oficial(u: Usuario, nome: str) -> dict:
    return {"id": u.id, "nome": nome, "perfil": u.perfil}


# ---------- disponibilidade (só o próprio oficial) ----------

@router.get("/disponibilidades", response_model=list[DisponibilidadeOut])
def listar_disponibilidades(ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.listar_disponibilidades(ator)


@router.post(
    "/disponibilidades", response_model=DisponibilidadeOut, status_code=status.HTTP_201_CREATED
)
def criar_disponibilidade(data: DisponibilidadeCreate, ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.criar_disponibilidade(ator, data)


@router.patch("/disponibilidades/{disp_id}", response_model=DisponibilidadeOut)
def atualizar_disponibilidade(
    disp_id: uuid.UUID, data: DisponibilidadeUpdate, ator: ActiveUser, controller: AtendimentoCtrl
) -> DisponibilidadeAtendimento:
    return controller.atualizar_disponibilidade(ator, disp_id, data)


@router.delete("/disponibilidades/{disp_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_disponibilidade(disp_id: uuid.UUID, ator: ActiveUser, controller: AtendimentoCtrl):
    controller.remover_disponibilidade(ator, disp_id)


# ---------- bloqueios de agenda (só o próprio oficial) ----------

@router.get("/bloqueios", response_model=list[BloqueioOut])
def listar_bloqueios(ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.listar_bloqueios(ator)


@router.post("/bloqueios", response_model=BloqueioOut, status_code=status.HTTP_201_CREATED)
def criar_bloqueio(data: BloqueioCreate, ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.criar_bloqueio(ator, data)


@router.delete("/bloqueios/{bloqueio_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_bloqueio(bloqueio_id: uuid.UUID, ator: ActiveUser, controller: AtendimentoCtrl):
    controller.remover_bloqueio(ator, bloqueio_id)


# ---------- relatório (só o próprio oficial) ----------

@router.get("/relatorio", response_model=list[RelatorioMesOut])
def relatorio(
    ator: ActiveUser,
    controller: AtendimentoCtrl,
    de: date | None = Query(default=None),
    ate: date | None = Query(default=None),
):
    return controller.relatorio(ator, de, ate)


# ---------- oficiais e horários livres ----------

@router.get("/meus-horarios", response_model=list[HorarioOut])
def meus_horarios(
    ator: ActiveUser,
    controller: AtendimentoCtrl,
    de: date | None = Query(default=None),
    ate: date | None = Query(default=None),
):
    """Horários livres da própria agenda do oficial (para propor uma remarcação)."""
    return controller.horarios_proprios(ator, de, ate)


@router.get("/oficiais", response_model=list[OficialOut])
def listar_oficiais(ator: ActiveUser, controller: AtendimentoCtrl):
    return [_oficial(u, nome) for u, nome in controller.listar_oficiais(ator)]


@router.get("/oficiais/{oficial_id}/horarios", response_model=list[HorarioOut])
def horarios_livres(
    oficial_id: uuid.UUID,
    ator: ActiveUser,
    controller: AtendimentoCtrl,
    de: date | None = Query(default=None),
    ate: date | None = Query(default=None),
):
    return controller.horarios_livres(ator, oficial_id, de, ate)


# ---------- atendimentos ----------

@router.post("/atendimentos", response_model=AtendimentoOut, status_code=status.HTTP_201_CREATED)
def solicitar(data: AtendimentoCreate, ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.solicitar(ator, data)


@router.get("/atendimentos/meus", response_model=list[AtendimentoOut])
def meus(
    ator: ActiveUser,
    controller: AtendimentoCtrl,
    status: StatusAtendimento | None = Query(default=None),
):
    return controller.listar_meus(ator, status)


@router.get("/atendimentos/recebidos", response_model=list[AtendimentoOut])
def recebidos(
    ator: ActiveUser,
    controller: AtendimentoCtrl,
    status: StatusAtendimento | None = Query(default=None),
):
    return controller.listar_recebidos(ator, status)


@router.get("/atendimentos/{atendimento_id}", response_model=AtendimentoOut)
def detalhe(atendimento_id: uuid.UUID, ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.get(ator, atendimento_id)


@router.post("/atendimentos/{atendimento_id}/confirmar", response_model=AtendimentoOut)
def confirmar(atendimento_id: uuid.UUID, ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.confirmar(ator, atendimento_id)


@router.post("/atendimentos/{atendimento_id}/recusar", response_model=AtendimentoOut)
def recusar(
    atendimento_id: uuid.UUID,
    ator: ActiveUser,
    controller: AtendimentoCtrl,
    data: JustificativaIn | None = None,
):
    return controller.recusar(ator, atendimento_id, data.justificativa if data else None)


@router.post("/atendimentos/{atendimento_id}/cancelar", response_model=AtendimentoOut)
def cancelar(
    atendimento_id: uuid.UUID,
    ator: ActiveUser,
    controller: AtendimentoCtrl,
    data: JustificativaIn | None = None,
):
    return controller.cancelar(ator, atendimento_id, data.justificativa if data else None)


@router.post("/atendimentos/{atendimento_id}/remarcar", response_model=AtendimentoOut)
def remarcar(
    atendimento_id: uuid.UUID, data: RemarcacaoIn, ator: ActiveUser, controller: AtendimentoCtrl
):
    return controller.remarcar(ator, atendimento_id, data)


@router.post("/atendimentos/{atendimento_id}/aceitar-remarcacao", response_model=AtendimentoOut)
def aceitar_remarcacao(atendimento_id: uuid.UUID, ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.aceitar_remarcacao(ator, atendimento_id)


@router.post("/atendimentos/{atendimento_id}/concluir", response_model=AtendimentoOut)
def concluir(atendimento_id: uuid.UUID, ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.concluir(ator, atendimento_id)


@router.post("/atendimentos/{atendimento_id}/faltou", response_model=AtendimentoOut)
def faltou(atendimento_id: uuid.UUID, ator: ActiveUser, controller: AtendimentoCtrl):
    return controller.faltou(ator, atendimento_id)
