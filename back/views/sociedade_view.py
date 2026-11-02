import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from models import Reuniao, Socio, Sociedade
from schemas import (
    FrequenciaOut,
    PresencasLote,
    ReuniaoCreate,
    ReuniaoDetalheOut,
    ReuniaoOut,
    ReuniaoUpdate,
    SocioCreate,
    SocioOut,
    SociedadeCreate,
    SociedadeOut,
    SociedadeUpdate,
    SocioUpdate,
)
from views.dependencies import GestorUser, SociedadeCtrl

# Sociedades internas: só admin e pastor (leitura e escrita)
router = APIRouter(prefix="/sociedades", tags=["sociedades"])


def _sociedade(s: Sociedade, total: int) -> dict:
    return {"id": s.id, "sigla": s.sigla, "nome": s.nome, "total_socios": total}


def _socio(s: Socio, nome: str) -> dict:
    return {
        "id": s.id,
        "sociedade_id": s.sociedade_id,
        "membro_id": s.membro_id,
        "nome": nome,
        "tipo": s.tipo,
        "entrou_em": s.entrou_em,
        "saiu_em": s.saiu_em,
    }


def _reuniao(r: Reuniao, p: int, a: int, j: int) -> dict:
    return {
        "id": r.id,
        "sociedade_id": r.sociedade_id,
        "data": r.data,
        "tema": r.tema,
        "presentes": p,
        "ausentes": a,
        "justificados": j,
    }


# ---------- sociedades ----------

@router.get("", response_model=list[SociedadeOut])
def listar(ator: GestorUser, controller: SociedadeCtrl):
    return [_sociedade(s, t) for s, t in controller.listar(ator)]


@router.post("", response_model=SociedadeOut, status_code=status.HTTP_201_CREATED)
def criar(data: SociedadeCreate, ator: GestorUser, controller: SociedadeCtrl):
    return _sociedade(*controller.criar(ator, data))


@router.get("/{sociedade_id}", response_model=SociedadeOut)
def obter(sociedade_id: uuid.UUID, ator: GestorUser, controller: SociedadeCtrl):
    return _sociedade(*controller.get_com_total(ator, sociedade_id))


@router.patch("/{sociedade_id}", response_model=SociedadeOut)
def atualizar(
    sociedade_id: uuid.UUID, data: SociedadeUpdate, ator: GestorUser, controller: SociedadeCtrl
):
    return _sociedade(*controller.atualizar(ator, sociedade_id, data))


# ---------- sócios ----------

@router.get("/{sociedade_id}/socios", response_model=list[SocioOut])
def listar_socios(
    sociedade_id: uuid.UUID,
    ator: GestorUser,
    controller: SociedadeCtrl,
    incluir_ex: bool = Query(False, description="Inclui quem já saiu da sociedade"),
):
    return [_socio(s, n) for s, n in controller.listar_socios(ator, sociedade_id, incluir_ex)]


@router.post(
    "/{sociedade_id}/socios", response_model=SocioOut, status_code=status.HTTP_201_CREATED
)
def adicionar_socio(
    sociedade_id: uuid.UUID, data: SocioCreate, ator: GestorUser, controller: SociedadeCtrl
):
    return _socio(*controller.adicionar_socio(ator, sociedade_id, data))


@router.patch("/{sociedade_id}/socios/{socio_id}", response_model=SocioOut)
def atualizar_socio(
    sociedade_id: uuid.UUID,
    socio_id: uuid.UUID,
    data: SocioUpdate,
    ator: GestorUser,
    controller: SociedadeCtrl,
):
    return _socio(*controller.atualizar_socio(ator, sociedade_id, socio_id, data))


@router.delete("/{sociedade_id}/socios/{socio_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_socio(
    sociedade_id: uuid.UUID, socio_id: uuid.UUID, ator: GestorUser, controller: SociedadeCtrl
):
    """O sócio sai da sociedade (data de saída); a presença histórica é mantida."""
    controller.remover_socio(ator, sociedade_id, socio_id)


# ---------- reuniões e presença ----------

@router.get("/{sociedade_id}/reunioes", response_model=list[ReuniaoOut])
def listar_reunioes(sociedade_id: uuid.UUID, ator: GestorUser, controller: SociedadeCtrl):
    return [_reuniao(*linha) for linha in controller.listar_reunioes(ator, sociedade_id)]


@router.post(
    "/{sociedade_id}/reunioes", response_model=ReuniaoDetalheOut, status_code=status.HTTP_201_CREATED
)
def criar_reuniao(
    sociedade_id: uuid.UUID, data: ReuniaoCreate, ator: GestorUser, controller: SociedadeCtrl
):
    reuniao = controller.criar_reuniao(ator, sociedade_id, data)
    return _detalhe(controller, ator, sociedade_id, reuniao.id)


@router.get("/{sociedade_id}/reunioes/{reuniao_id}", response_model=ReuniaoDetalheOut)
def obter_reuniao(
    sociedade_id: uuid.UUID, reuniao_id: uuid.UUID, ator: GestorUser, controller: SociedadeCtrl
):
    return _detalhe(controller, ator, sociedade_id, reuniao_id)


@router.patch("/{sociedade_id}/reunioes/{reuniao_id}", response_model=ReuniaoDetalheOut)
def atualizar_reuniao(
    sociedade_id: uuid.UUID,
    reuniao_id: uuid.UUID,
    data: ReuniaoUpdate,
    ator: GestorUser,
    controller: SociedadeCtrl,
):
    controller.atualizar_reuniao(ator, sociedade_id, reuniao_id, data)
    return _detalhe(controller, ator, sociedade_id, reuniao_id)


@router.put("/{sociedade_id}/reunioes/{reuniao_id}/presencas", response_model=ReuniaoDetalheOut)
def lancar_presencas(
    sociedade_id: uuid.UUID,
    reuniao_id: uuid.UUID,
    data: PresencasLote,
    ator: GestorUser,
    controller: SociedadeCtrl,
):
    """Lançamento em lote: cria ou corrige a presença de cada sócio informado.
    Sócios que não constam na lista não são alterados."""
    controller.lancar_presencas(ator, sociedade_id, reuniao_id, data.presencas)
    return _detalhe(controller, ator, sociedade_id, reuniao_id)


def _detalhe(controller, ator, sociedade_id: uuid.UUID, reuniao_id: uuid.UUID) -> dict:
    reuniao, presencas = controller.detalhe_reuniao(ator, sociedade_id, reuniao_id)
    p, a, j = controller.contagem(reuniao.id)
    return {
        **_reuniao(reuniao, p, a, j),
        "presencas": [
            {"socio_id": pr.socio_id, "nome": nome, "status": pr.status} for pr, nome in presencas
        ],
    }


# ---------- frequência ----------

@router.get("/{sociedade_id}/frequencia", response_model=FrequenciaOut)
def frequencia(
    sociedade_id: uuid.UUID,
    ator: GestorUser,
    controller: SociedadeCtrl,
    de: date | None = Query(None, description="Primeira data do período (inclusive)"),
    ate: date | None = Query(None, description="Última data do período (inclusive)"),
):
    return controller.frequencia(ator, sociedade_id, de, ate)
