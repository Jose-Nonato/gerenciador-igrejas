import uuid
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from models import Usuario
from models.ebd import EbdAluno, EbdAula, EbdClasse, EbdProfessor
from models.enums import PerfilUsuario, SituacaoMembro, StatusPresenca
from repositories import AuditoriaRepository, EbdRepository, MembroRepository
from schemas import (
    EbdAlunoCreate,
    EbdAlunoUpdate,
    EbdAulaCreate,
    EbdAulaUpdate,
    EbdClasseCreate,
    EbdClasseUpdate,
    EbdPresencaItem,
    EbdProfessorCreate,
    EbdProfessorUpdate,
)

# Quem já saiu do rol não pode ser professor nem aluno
_FORA_DO_ROL = {SituacaoMembro.TRANSFERIDO, SituacaoMembro.FALECIDO, SituacaoMembro.EXCLUIDO}


class EbdController:
    """Escola Bíblica Dominical.

    Admin e pastor acessam todas as classes e são os únicos que criam classes, mudam o nome,
    ativam/desativam e definem os professores. O professor em exercício numa classe vê e edita
    só a dela (alunos, aulas e presença). A autorização por classe está em `get`, pelo qual
    passa toda operação por classe.
    """

    def __init__(
        self, ebd: EbdRepository, membros: MembroRepository, audit: AuditoriaRepository, db: Session
    ) -> None:
        self.ebd = ebd
        self.membros = membros
        self.audit = audit
        self.db = db

    # ---------- acesso ----------

    @staticmethod
    def _e_gestor(ator: Usuario) -> bool:
        return ator.perfil in (PerfilUsuario.ADMIN, PerfilUsuario.PASTOR)

    def _classes_do_ator(self, ator: Usuario) -> set[uuid.UUID]:
        if ator.membro_id is None:
            return set()
        return self.ebd.classes_do_professor(ator.igreja_id, ator.membro_id)

    def tem_acesso(self, ator: Usuario) -> bool:
        return self._e_gestor(ator) or bool(self._classes_do_ator(ator))

    def get(
        self, ator: Usuario, classe_id: uuid.UUID, *, so_gestor: bool = False, escrita: bool = False
    ) -> EbdClasse:
        # Sempre filtrado pela igreja do ator: outra igreja aparece como inexistente
        classe = self.ebd.get_classe(ator.igreja_id, classe_id)
        if classe is None:
            raise NotFoundError("Classe não encontrada")
        if not self._e_gestor(ator):
            if so_gestor:
                raise ForbiddenError("Apenas administrador e pastor podem fazer isso")
            if classe.id not in self._classes_do_ator(ator):
                raise ForbiddenError("Você não é professor desta classe")
        if escrita and not classe.ativa:
            raise ConflictError("Esta classe está desativada. Reative-a para alterar")
        return classe

    # ---------- classes ----------

    def listar(self, ator: Usuario) -> list[tuple[EbdClasse, int, int]]:
        if self._e_gestor(ator):
            return self.ebd.list_classes(ator.igreja_id)
        return self.ebd.list_classes(ator.igreja_id, ids=self._classes_do_ator(ator))

    def get_com_totais(self, ator: Usuario, classe_id: uuid.UUID) -> tuple[EbdClasse, int, int]:
        self.get(ator, classe_id)
        achado = self.ebd.get_classe_com_totais(ator.igreja_id, classe_id)
        assert achado is not None
        return achado

    def criar(self, ator: Usuario, data: EbdClasseCreate) -> tuple[EbdClasse, int, int]:
        if self.ebd.classe_por_nome(ator.igreja_id, data.nome):
            raise ConflictError("Já existe uma classe com este nome")
        classe = self.ebd.create_classe(
            ator.igreja_id, {"nome": data.nome, "faixa_etaria": data.faixa_etaria}
        )
        self.audit.registrar(
            ator.igreja_id, ator.id, "ebd_classe_criada", "ebd_classe", classe.id,
            {"nome": classe.nome}, commit=False,
        )
        self._commit("Já existe uma classe com este nome")
        return classe, 0, 0

    def atualizar(
        self, ator: Usuario, classe_id: uuid.UUID, data: EbdClasseUpdate
    ) -> tuple[EbdClasse, int, int]:
        classe = self.get(ator, classe_id, so_gestor=True)
        campos = data.model_dump(exclude_unset=True)
        if "nome" in campos and campos["nome"].lower() != classe.nome.lower():
            if self.ebd.classe_por_nome(ator.igreja_id, campos["nome"], ignorar_id=classe.id):
                raise ConflictError("Já existe uma classe com este nome")
        self.ebd.apply(classe, campos)
        self.audit.registrar(
            ator.igreja_id, ator.id, "ebd_classe_alterada", "ebd_classe", classe.id,
            {"campos": sorted(campos)}, commit=False,
        )
        self._commit("Já existe uma classe com este nome")
        return self.get_com_totais(ator, classe.id)

    def buscar_membros(self, ator: Usuario, classe_id: uuid.UUID, q: str) -> list:
        """Busca só com o necessário (nome e nº do rol), para o professor poder matricular
        alunos sem ter acesso ao rol completo."""
        self.get(ator, classe_id)
        return self.membros.buscar_elegiveis(ator.igreja_id, q, limit=10)

    # ---------- professores ----------

    def listar_professores(
        self, ator: Usuario, classe_id: uuid.UUID, incluir_encerrados: bool
    ) -> list[tuple[EbdProfessor, str]]:
        self.get(ator, classe_id)
        return self.ebd.list_professores(ator.igreja_id, classe_id, incluir_encerrados)

    def adicionar_professor(
        self, ator: Usuario, classe_id: uuid.UUID, data: EbdProfessorCreate
    ) -> tuple[EbdProfessor, str]:
        classe = self.get(ator, classe_id, so_gestor=True, escrita=True)
        membro = self.membros.get_in_church(ator.igreja_id, data.membro_id)
        if membro is None:
            raise NotFoundError("Membro não encontrado")
        if membro.situacao in _FORA_DO_ROL:
            raise ConflictError("Este membro não faz mais parte do rol")
        if self.ebd.professor_ativo(classe.id, membro.id):
            raise ConflictError("Este membro já é professor desta classe")

        campos = {"membro_id": membro.id}
        if data.inicio is not None:
            campos["inicio"] = data.inicio
        professor = self.ebd.create_professor(ator.igreja_id, classe.id, campos)
        self.audit.registrar(
            ator.igreja_id, ator.id, "ebd_professor_adicionado", "ebd_professor", professor.id,
            {"classe": classe.nome, "nome": membro.nome}, commit=False,
        )
        self._commit("Este membro já é professor desta classe")
        return professor, membro.nome

    def atualizar_professor(
        self, ator: Usuario, classe_id: uuid.UUID, professor_id: uuid.UUID, data: EbdProfessorUpdate
    ) -> tuple[EbdProfessor, str]:
        self.get(ator, classe_id, so_gestor=True)
        achado = self.ebd.get_professor(ator.igreja_id, classe_id, professor_id)
        if achado is None:
            raise NotFoundError("Professor não encontrado")
        professor, nome = achado

        inicio = data.inicio or professor.inicio
        fim = data.fim if data.fim is not None else professor.fim
        if fim is not None and fim < inicio:
            raise AppError("O fim não pode ser antes do início")

        encerrando = professor.fim is None and data.fim is not None
        campos = {}
        if data.inicio is not None:
            campos["inicio"] = data.inicio
        if data.fim is not None:
            campos["fim"] = data.fim
        self.ebd.apply(professor, campos)
        self.audit.registrar(
            ator.igreja_id, ator.id,
            "ebd_professor_encerrado" if encerrando else "ebd_professor_alterado",
            "ebd_professor", professor.id,
            {"nome": nome, **{k: v.isoformat() for k, v in campos.items()}}, commit=False,
        )
        self._commit()
        return professor, nome

    # ---------- alunos ----------

    def listar_alunos(
        self, ator: Usuario, classe_id: uuid.UUID, incluir_ex: bool
    ) -> list[tuple[EbdAluno, str]]:
        self.get(ator, classe_id)
        return self.ebd.list_alunos(ator.igreja_id, classe_id, incluir_ex)

    def adicionar_aluno(
        self, ator: Usuario, classe_id: uuid.UUID, data: EbdAlunoCreate
    ) -> tuple[EbdAluno, str]:
        classe = self.get(ator, classe_id, escrita=True)
        nome = data.nome_externo
        if data.membro_id is not None:
            membro = self.membros.get_in_church(ator.igreja_id, data.membro_id)
            if membro is None:
                raise NotFoundError("Membro não encontrado")
            if membro.situacao in _FORA_DO_ROL:
                raise ConflictError("Este membro não faz mais parte do rol")
            if self.ebd.aluno_ativo_do_membro(classe.id, membro.id):
                raise ConflictError("Este membro já é aluno desta classe")
            nome = membro.nome

        aluno = self.ebd.create_aluno(
            ator.igreja_id, classe.id,
            {"membro_id": data.membro_id, "nome_externo": data.nome_externo},
        )
        self.audit.registrar(
            ator.igreja_id, ator.id, "ebd_aluno_adicionado", "ebd_aluno", aluno.id,
            {"classe": classe.nome, "nome": nome}, commit=False,
        )
        self._commit("Este membro já é aluno desta classe")
        return aluno, nome or ""

    def atualizar_aluno(
        self, ator: Usuario, classe_id: uuid.UUID, aluno_id: uuid.UUID, data: EbdAlunoUpdate
    ) -> tuple[EbdAluno, str]:
        aluno, _ = self._get_aluno(ator, classe_id, aluno_id)
        if aluno.saiu_em is not None:
            raise ConflictError("Aluno que já saiu não pode ser alterado")
        if aluno.membro_id is not None:
            raise AppError("O nome só pode ser alterado para visitantes")
        nome = data.nome_externo.strip()
        if not nome:
            raise AppError("Informe o nome")
        self.ebd.apply(aluno, {"nome_externo": nome})
        self.audit.registrar(
            ator.igreja_id, ator.id, "ebd_aluno_alterado", "ebd_aluno", aluno.id,
            {"nome": nome}, commit=False,
        )
        self._commit()
        return aluno, nome

    def remover_aluno(self, ator: Usuario, classe_id: uuid.UUID, aluno_id: uuid.UUID) -> None:
        """O aluno sai da classe (data de saída); a presença histórica é mantida."""
        aluno, nome = self._get_aluno(ator, classe_id, aluno_id)
        if aluno.saiu_em is not None:
            raise ConflictError("Este aluno já saiu da classe")
        self.ebd.apply(aluno, {"saiu_em": date.today()})
        self.audit.registrar(
            ator.igreja_id, ator.id, "ebd_aluno_removido", "ebd_aluno", aluno.id,
            {"nome": nome}, commit=False,
        )
        self._commit()

    # ---------- aulas ----------

    def listar_aulas(
        self, ator: Usuario, classe_id: uuid.UUID
    ) -> list[tuple[EbdAula, int, int, int]]:
        self.get(ator, classe_id)
        return self.ebd.list_aulas(ator.igreja_id, classe_id)

    def criar_aula(self, ator: Usuario, classe_id: uuid.UUID, data: EbdAulaCreate) -> EbdAula:
        classe = self.get(ator, classe_id, escrita=True)
        if self.ebd.aula_na_data(classe.id, data.data):
            raise ConflictError("Já existe uma aula nesta data")
        # Valida tudo antes de gravar qualquer coisa
        itens = self._validar_presencas(ator, classe.id, data.data, data.presencas)

        aula = self.ebd.create_aula(ator.igreja_id, classe.id, data.data, data.licao)
        if itens:
            self.ebd.upsert_presencas(ator.igreja_id, aula.id, itens)
        self.audit.registrar(
            ator.igreja_id, ator.id, "ebd_aula_criada", "ebd_aula", aula.id,
            {"classe": classe.nome, "data": data.data.isoformat(), "presencas": len(itens)},
            commit=False,
        )
        self._commit("Já existe uma aula nesta data")
        return aula

    def atualizar_aula(
        self, ator: Usuario, classe_id: uuid.UUID, aula_id: uuid.UUID, data: EbdAulaUpdate
    ) -> EbdAula:
        aula = self._get_aula(ator, classe_id, aula_id)
        campos: dict = {}
        if data.data is not None and data.data != aula.data:
            if self.ebd.aula_na_data(classe_id, data.data, ignorar_id=aula.id):
                raise ConflictError("Já existe uma aula nesta data")
            campos["data"] = data.data
        if "licao" in data.model_fields_set:
            campos["licao"] = data.licao
        if campos:
            self.ebd.apply(aula, campos)
            self._commit("Já existe uma aula nesta data")
        return aula

    def contagem(self, aula_id: uuid.UUID) -> tuple[int, int, int]:
        return self.ebd.contagem_da_aula(aula_id)

    def detalhe_aula(
        self, ator: Usuario, classe_id: uuid.UUID, aula_id: uuid.UUID
    ) -> tuple[EbdAula, list]:
        aula = self._get_aula(ator, classe_id, aula_id, escrita=False)
        return aula, self.ebd.list_presencas(aula.id)

    def lancar_presencas(
        self,
        ator: Usuario,
        classe_id: uuid.UUID,
        aula_id: uuid.UUID,
        presencas: list[EbdPresencaItem],
    ) -> EbdAula:
        """Lançamento em lote: cria ou corrige a presença de cada aluno informado."""
        aula = self._get_aula(ator, classe_id, aula_id)
        itens = self._validar_presencas(ator, classe_id, aula.data, presencas)
        if itens:
            self.ebd.upsert_presencas(ator.igreja_id, aula.id, itens)
            self.audit.registrar(
                ator.igreja_id, ator.id, "ebd_presencas_lancadas", "ebd_aula", aula.id,
                {"registros": len(itens)}, commit=False,
            )
            self._commit()
        return aula

    # ---------- frequência ----------

    def frequencia(
        self, ator: Usuario, classe_id: uuid.UUID, de: date | None, ate: date | None
    ) -> dict:
        self.get(ator, classe_id)
        if de and ate and de > ate:
            raise AppError("A data inicial não pode ser depois da final")

        total = self.ebd.total_aulas(classe_id, de, ate)
        por_aluno = self.ebd.contagem_por_aluno(classe_id, de, ate)
        linhas = []
        for aluno, nome in self.ebd.list_alunos(ator.igreja_id, classe_id, incluir_ex=True):
            c = por_aluno.get(aluno.id, {})
            p = c.get(StatusPresenca.PRESENTE, 0)
            a = c.get(StatusPresenca.AUSENTE, 0)
            j = c.get(StatusPresenca.JUSTIFICADO, 0)
            registrados = p + a + j
            # Quem já saiu só aparece se tiver presença no período
            if aluno.saiu_em is not None and registrados == 0:
                continue
            linhas.append(
                {
                    "aluno_id": aluno.id,
                    "nome": nome,
                    "presentes": p,
                    "ausentes": a,
                    "justificados": j,
                    "sem_registro": max(total - registrados, 0),
                    "percentual_presenca": round(100 * p / registrados, 1) if registrados else None,
                }
            )
        return {"de": de, "ate": ate, "total_aulas": total, "alunos": linhas}

    # ---------- internos ----------

    def _get_aluno(
        self, ator: Usuario, classe_id: uuid.UUID, aluno_id: uuid.UUID
    ) -> tuple[EbdAluno, str]:
        self.get(ator, classe_id, escrita=True)
        achado = self.ebd.get_aluno(ator.igreja_id, classe_id, aluno_id)
        if achado is None:
            raise NotFoundError("Aluno não encontrado")
        return achado

    def _get_aula(
        self, ator: Usuario, classe_id: uuid.UUID, aula_id: uuid.UUID, escrita: bool = True
    ) -> EbdAula:
        self.get(ator, classe_id, escrita=escrita)
        aula = self.ebd.get_aula(ator.igreja_id, classe_id, aula_id)
        if aula is None:
            raise NotFoundError("Aula não encontrada")
        return aula

    def _validar_presencas(
        self,
        ator: Usuario,
        classe_id: uuid.UUID,
        data_aula: date,
        presencas: list[EbdPresencaItem],
    ) -> dict[uuid.UUID, StatusPresenca]:
        itens: dict[uuid.UUID, StatusPresenca] = {}
        for item in presencas:
            achado = self.ebd.get_aluno(ator.igreja_id, classe_id, item.aluno_id)
            if achado is None:
                raise NotFoundError("Aluno não encontrado nesta classe")
            aluno, nome = achado
            if aluno.saiu_em is not None and aluno.saiu_em < data_aula:
                raise ConflictError(f"{nome} já havia saído da classe nesta data")
            itens[aluno.id] = item.status
        return itens

    def _commit(self, mensagem_conflito: str = "Registro duplicado") -> None:
        try:
            self.db.commit()
        except IntegrityError:
            # Corrida entre duas requisições iguais: a restrição única do banco decide
            self.db.rollback()
            raise ConflictError(mensagem_conflito)
