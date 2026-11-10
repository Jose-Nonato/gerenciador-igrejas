import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from models.ebd import EbdAluno, EbdAula, EbdClasse, EbdProfessor
from schemas import (
    EbdAlunoCreate,
    EbdAlunoOut,
    EbdAlunoUpdate,
    EbdAulaCreate,
    EbdAulaDetalheOut,
    EbdAulaOut,
    EbdAulaUpdate,
    EbdClasseCreate,
    EbdClasseOut,
    EbdClasseUpdate,
    EbdFrequenciaOut,
    EbdPresencasLote,
    EbdProfessorCreate,
    EbdProfessorOut,
    EbdProfessorUpdate,
    MembroResumo,
)
from views.dependencies import ActiveUser, EbdCtrl, GestorUser

# Escola Bíblica Dominical. Admin e pastor acessam todas as classes e são os únicos que criam
# classes, mudam o nome e definem os professores. O professor em exercício vê e edita só a
# sua classe: a autorização por classe fica em EbdController.get.
router = APIRouter(prefix="/ebd/classes", tags=["ebd"])


def _classe(c: EbdClasse, alunos: int, professores: int) -> dict:
    return {
        "id": c.id,
        "nome": c.nome,
        "faixa_etaria": c.faixa_etaria,
        "ativa": c.ativa,
        "total_alunos": alunos,
        "total_professores": professores,
    }


def _professor(p: EbdProfessor, nome: str) -> dict:
    return {
        "id": p.id,
        "classe_id": p.classe_id,
        "membro_id": p.membro_id,
        "nome": nome,
        "inicio": p.inicio,
        "fim": p.fim,
    }


def _aluno(a: EbdAluno, nome: str) -> dict:
    return {
        "id": a.id,
        "classe_id": a.classe_id,
        "membro_id": a.membro_id,
        "nome": nome,
        "entrou_em": a.entrou_em,
        "saiu_em": a.saiu_em,
    }


def _aula(a: EbdAula, p: int, au: int, j: int) -> dict:
    return {
        "id": a.id,
        "classe_id": a.classe_id,
        "data": a.data,
        "licao": a.licao,
        "presentes": p,
        "ausentes": au,
        "justificados": j,
    }


def _detalhe(controller, ator, classe_id: uuid.UUID, aula_id: uuid.UUID) -> dict:
    aula, presencas = controller.detalhe_aula(ator, classe_id, aula_id)
    p, a, j = controller.contagem(aula.id)
    return {
        **_aula(aula, p, a, j),
        "presencas": [
            {"aluno_id": pr.aluno_id, "nome": nome, "status": pr.status} for pr, nome in presencas
        ],
    }


# ---------- classes ----------

@router.get("", response_model=list[EbdClasseOut])
def listar(ator: ActiveUser, controller: EbdCtrl):
    return [_classe(*linha) for linha in controller.listar(ator)]


@router.post("", response_model=EbdClasseOut, status_code=status.HTTP_201_CREATED)
def criar(data: EbdClasseCreate, ator: GestorUser, controller: EbdCtrl):
    return _classe(*controller.criar(ator, data))


@router.get("/{classe_id}", response_model=EbdClasseOut)
def obter(classe_id: uuid.UUID, ator: ActiveUser, controller: EbdCtrl):
    return _classe(*controller.get_com_totais(ator, classe_id))


@router.patch("/{classe_id}", response_model=EbdClasseOut)
def atualizar(classe_id: uuid.UUID, data: EbdClasseUpdate, ator: GestorUser, controller: EbdCtrl):
    return _classe(*controller.atualizar(ator, classe_id, data))


@router.get("/{classe_id}/membros", response_model=list[MembroResumo])
def buscar_membros(
    classe_id: uuid.UUID,
    ator: ActiveUser,
    controller: EbdCtrl,
    q: str = Query(min_length=2, max_length=100, description="Parte do nome"),
):
    """Busca mínima (nome e nº do rol) de membros que ainda fazem parte do rol."""
    return controller.buscar_membros(ator, classe_id, q)


# ---------- professores ----------

@router.get("/{classe_id}/professores", response_model=list[EbdProfessorOut])
def listar_professores(
    classe_id: uuid.UUID,
    ator: ActiveUser,
    controller: EbdCtrl,
    incluir_encerrados: bool = Query(False, description="Inclui quem já deixou a classe"),
):
    return [
        _professor(p, n) for p, n in controller.listar_professores(ator, classe_id, incluir_encerrados)
    ]


@router.post(
    "/{classe_id}/professores", response_model=EbdProfessorOut, status_code=status.HTTP_201_CREATED
)
def adicionar_professor(
    classe_id: uuid.UUID, data: EbdProfessorCreate, ator: GestorUser, controller: EbdCtrl
):
    return _professor(*controller.adicionar_professor(ator, classe_id, data))


@router.patch("/{classe_id}/professores/{professor_id}", response_model=EbdProfessorOut)
def atualizar_professor(
    classe_id: uuid.UUID,
    professor_id: uuid.UUID,
    data: EbdProfessorUpdate,
    ator: GestorUser,
    controller: EbdCtrl,
):
    """Corrige as datas ou encerra o exercício (`fim`); o histórico é mantido."""
    return _professor(*controller.atualizar_professor(ator, classe_id, professor_id, data))


# ---------- alunos ----------

@router.get("/{classe_id}/alunos", response_model=list[EbdAlunoOut])
def listar_alunos(
    classe_id: uuid.UUID,
    ator: ActiveUser,
    controller: EbdCtrl,
    incluir_ex: bool = Query(False, description="Inclui quem já saiu da classe"),
):
    return [_aluno(a, n) for a, n in controller.listar_alunos(ator, classe_id, incluir_ex)]


@router.post(
    "/{classe_id}/alunos", response_model=EbdAlunoOut, status_code=status.HTTP_201_CREATED
)
def adicionar_aluno(
    classe_id: uuid.UUID, data: EbdAlunoCreate, ator: ActiveUser, controller: EbdCtrl
):
    return _aluno(*controller.adicionar_aluno(ator, classe_id, data))


@router.patch("/{classe_id}/alunos/{aluno_id}", response_model=EbdAlunoOut)
def atualizar_aluno(
    classe_id: uuid.UUID,
    aluno_id: uuid.UUID,
    data: EbdAlunoUpdate,
    ator: ActiveUser,
    controller: EbdCtrl,
):
    return _aluno(*controller.atualizar_aluno(ator, classe_id, aluno_id, data))


@router.delete("/{classe_id}/alunos/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_aluno(
    classe_id: uuid.UUID, aluno_id: uuid.UUID, ator: ActiveUser, controller: EbdCtrl
):
    """O aluno sai da classe (data de saída); a presença histórica é mantida."""
    controller.remover_aluno(ator, classe_id, aluno_id)


# ---------- aulas e presença ----------

@router.get("/{classe_id}/aulas", response_model=list[EbdAulaOut])
def listar_aulas(classe_id: uuid.UUID, ator: ActiveUser, controller: EbdCtrl):
    return [_aula(*linha) for linha in controller.listar_aulas(ator, classe_id)]


@router.post(
    "/{classe_id}/aulas", response_model=EbdAulaDetalheOut, status_code=status.HTTP_201_CREATED
)
def criar_aula(classe_id: uuid.UUID, data: EbdAulaCreate, ator: ActiveUser, controller: EbdCtrl):
    aula = controller.criar_aula(ator, classe_id, data)
    return _detalhe(controller, ator, classe_id, aula.id)


@router.get("/{classe_id}/aulas/{aula_id}", response_model=EbdAulaDetalheOut)
def obter_aula(classe_id: uuid.UUID, aula_id: uuid.UUID, ator: ActiveUser, controller: EbdCtrl):
    return _detalhe(controller, ator, classe_id, aula_id)


@router.patch("/{classe_id}/aulas/{aula_id}", response_model=EbdAulaDetalheOut)
def atualizar_aula(
    classe_id: uuid.UUID,
    aula_id: uuid.UUID,
    data: EbdAulaUpdate,
    ator: ActiveUser,
    controller: EbdCtrl,
):
    controller.atualizar_aula(ator, classe_id, aula_id, data)
    return _detalhe(controller, ator, classe_id, aula_id)


@router.put("/{classe_id}/aulas/{aula_id}/presencas", response_model=EbdAulaDetalheOut)
def lancar_presencas(
    classe_id: uuid.UUID,
    aula_id: uuid.UUID,
    data: EbdPresencasLote,
    ator: ActiveUser,
    controller: EbdCtrl,
):
    """Lançamento em lote: cria ou corrige a presença de cada aluno informado.
    Alunos que não constam na lista não são alterados."""
    controller.lancar_presencas(ator, classe_id, aula_id, data.presencas)
    return _detalhe(controller, ator, classe_id, aula_id)


# ---------- frequência ----------

@router.get("/{classe_id}/frequencia", response_model=EbdFrequenciaOut)
def frequencia(
    classe_id: uuid.UUID,
    ator: ActiveUser,
    controller: EbdCtrl,
    de: date | None = Query(None, description="Primeira data do período (inclusive)"),
    ate: date | None = Query(None, description="Última data do período (inclusive)"),
):
    return controller.frequencia(ator, classe_id, de, ate)
