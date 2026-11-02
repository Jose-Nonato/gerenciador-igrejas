import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from models import Lideranca, Reuniao, Socio, Sociedade
from schemas import (
    FrequenciaOut,
    LiderancaCreate,
    LiderancaOut,
    LiderancaUpdate,
    MembroResumo,
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
from views.dependencies import ActiveUser, GestorUser, SociedadeCtrl

# Sociedades internas. Admin e pastor acessam todas e são os únicos que criam sociedades,
# mudam o nome e alteram a diretoria. Quem está na diretoria (mandato em exercício) vê e
# edita só a sua sociedade: a autorização por sociedade fica em SociedadeController.get.
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


def _lideranca(item: Lideranca, nome: str) -> dict:
    return {
        "id": item.id,
        "sociedade_id": item.sociedade_id,
        "membro_id": item.membro_id,
        "nome": nome,
        "cargo": item.cargo,
        "cargo_descricao": item.cargo_descricao,
        "inicio": item.inicio,
        "fim": item.fim,
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
def listar(ator: ActiveUser, controller: SociedadeCtrl):
    return [_sociedade(s, t) for s, t in controller.listar(ator)]


@router.post("", response_model=SociedadeOut, status_code=status.HTTP_201_CREATED)
def criar(data: SociedadeCreate, ator: GestorUser, controller: SociedadeCtrl):
    return _sociedade(*controller.criar(ator, data))


@router.get("/{sociedade_id}", response_model=SociedadeOut)
def obter(sociedade_id: uuid.UUID, ator: ActiveUser, controller: SociedadeCtrl):
    return _sociedade(*controller.get_com_total(ator, sociedade_id))


@router.patch("/{sociedade_id}", response_model=SociedadeOut)
def atualizar(
    sociedade_id: uuid.UUID, data: SociedadeUpdate, ator: GestorUser, controller: SociedadeCtrl
):
    return _sociedade(*controller.atualizar(ator, sociedade_id, data))


# ---------- busca de membros (para cadastrar sócios) ----------

@router.get("/{sociedade_id}/membros", response_model=list[MembroResumo])
def buscar_membros(
    sociedade_id: uuid.UUID,
    ator: ActiveUser,
    controller: SociedadeCtrl,
    q: str = Query(min_length=2, max_length=100, description="Parte do nome"),
):
    """Busca mínima (nome e nº do rol) de membros que ainda fazem parte do rol."""
    return controller.buscar_membros(ator, sociedade_id, q)


# ---------- sócios ----------

@router.get("/{sociedade_id}/socios", response_model=list[SocioOut])
def listar_socios(
    sociedade_id: uuid.UUID,
    ator: ActiveUser,
    controller: SociedadeCtrl,
    incluir_ex: bool = Query(False, description="Inclui quem já saiu da sociedade"),
):
    return [_socio(s, n) for s, n in controller.listar_socios(ator, sociedade_id, incluir_ex)]


@router.post(
    "/{sociedade_id}/socios", response_model=SocioOut, status_code=status.HTTP_201_CREATED
)
def adicionar_socio(
    sociedade_id: uuid.UUID, data: SocioCreate, ator: ActiveUser, controller: SociedadeCtrl
):
    return _socio(*controller.adicionar_socio(ator, sociedade_id, data))


@router.patch("/{sociedade_id}/socios/{socio_id}", response_model=SocioOut)
def atualizar_socio(
    sociedade_id: uuid.UUID,
    socio_id: uuid.UUID,
    data: SocioUpdate,
    ator: ActiveUser,
    controller: SociedadeCtrl,
):
    return _socio(*controller.atualizar_socio(ator, sociedade_id, socio_id, data))


@router.delete("/{sociedade_id}/socios/{socio_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_socio(
    sociedade_id: uuid.UUID, socio_id: uuid.UUID, ator: ActiveUser, controller: SociedadeCtrl
):
    """O sócio sai da sociedade (data de saída); a presença histórica é mantida."""
    controller.remover_socio(ator, sociedade_id, socio_id)


# ---------- liderança (diretoria) ----------

@router.get("/{sociedade_id}/lideranca", response_model=list[LiderancaOut])
def listar_lideranca(
    sociedade_id: uuid.UUID,
    ator: ActiveUser,
    controller: SociedadeCtrl,
    incluir_encerrados: bool = Query(False, description="Inclui mandatos já encerrados"),
):
    itens = controller.listar_lideranca(ator, sociedade_id, incluir_encerrados)
    return [_lideranca(i, n) for i, n in itens]


@router.post(
    "/{sociedade_id}/lideranca", response_model=LiderancaOut, status_code=status.HTTP_201_CREATED
)
def adicionar_lideranca(
    sociedade_id: uuid.UUID, data: LiderancaCreate, ator: GestorUser, controller: SociedadeCtrl
):
    return _lideranca(*controller.adicionar_lideranca(ator, sociedade_id, data))


@router.patch("/{sociedade_id}/lideranca/{lideranca_id}", response_model=LiderancaOut)
def atualizar_lideranca(
    sociedade_id: uuid.UUID,
    lideranca_id: uuid.UUID,
    data: LiderancaUpdate,
    ator: GestorUser,
    controller: SociedadeCtrl,
):
    """Corrige as datas ou encerra o mandato (`fim`); o histórico é mantido."""
    return _lideranca(*controller.atualizar_lideranca(ator, sociedade_id, lideranca_id, data))


# ---------- reuniões e presença ----------

@router.get("/{sociedade_id}/reunioes", response_model=list[ReuniaoOut])
def listar_reunioes(sociedade_id: uuid.UUID, ator: ActiveUser, controller: SociedadeCtrl):
    return [_reuniao(*linha) for linha in controller.listar_reunioes(ator, sociedade_id)]


@router.post(
    "/{sociedade_id}/reunioes", response_model=ReuniaoDetalheOut, status_code=status.HTTP_201_CREATED
)
def criar_reuniao(
    sociedade_id: uuid.UUID, data: ReuniaoCreate, ator: ActiveUser, controller: SociedadeCtrl
):
    reuniao = controller.criar_reuniao(ator, sociedade_id, data)
    return _detalhe(controller, ator, sociedade_id, reuniao.id)


@router.get("/{sociedade_id}/reunioes/{reuniao_id}", response_model=ReuniaoDetalheOut)
def obter_reuniao(
    sociedade_id: uuid.UUID, reuniao_id: uuid.UUID, ator: ActiveUser, controller: SociedadeCtrl
):
    return _detalhe(controller, ator, sociedade_id, reuniao_id)


@router.patch("/{sociedade_id}/reunioes/{reuniao_id}", response_model=ReuniaoDetalheOut)
def atualizar_reuniao(
    sociedade_id: uuid.UUID,
    reuniao_id: uuid.UUID,
    data: ReuniaoUpdate,
    ator: ActiveUser,
    controller: SociedadeCtrl,
):
    controller.atualizar_reuniao(ator, sociedade_id, reuniao_id, data)
    return _detalhe(controller, ator, sociedade_id, reuniao_id)


@router.put("/{sociedade_id}/reunioes/{reuniao_id}/presencas", response_model=ReuniaoDetalheOut)
def lancar_presencas(
    sociedade_id: uuid.UUID,
    reuniao_id: uuid.UUID,
    data: PresencasLote,
    ator: ActiveUser,
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
    ator: ActiveUser,
    controller: SociedadeCtrl,
    de: date | None = Query(None, description="Primeira data do período (inclusive)"),
    ate: date | None = Query(None, description="Última data do período (inclusive)"),
):
    return controller.frequencia(ator, sociedade_id, de, ate)
