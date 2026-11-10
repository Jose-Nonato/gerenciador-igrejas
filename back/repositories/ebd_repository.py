import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.ebd import EbdAluno, EbdAula, EbdClasse, EbdPresenca, EbdProfessor
from models.enums import StatusPresenca
from models.membro import Membro

# Os métodos de escrita NÃO fazem commit: lançar presenças altera presença e auditoria na
# mesma transação, e o commit fica com o controller.

# Aluno cujo membro foi excluído (exclusão lógica) some das listagens
_ALUNO_VIVO = or_(EbdAluno.membro_id.is_(None), Membro.excluido_em.is_(None))
_NOME_ALUNO = func.coalesce(Membro.nome, EbdAluno.nome_externo)


class EbdRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def apply(self, entidade, campos: dict) -> None:
        for chave, valor in campos.items():
            setattr(entidade, chave, valor)
        self.db.flush()

    # ---------- classes ----------

    def get_classe(self, igreja_id: uuid.UUID, classe_id: uuid.UUID) -> EbdClasse | None:
        return self.db.scalar(
            select(EbdClasse).where(EbdClasse.id == classe_id, EbdClasse.igreja_id == igreja_id)
        )

    def classe_por_nome(
        self, igreja_id: uuid.UUID, nome: str, ignorar_id: uuid.UUID | None = None
    ) -> EbdClasse | None:
        consulta = select(EbdClasse).where(
            EbdClasse.igreja_id == igreja_id, func.lower(EbdClasse.nome) == nome.lower()
        )
        if ignorar_id:
            consulta = consulta.where(EbdClasse.id != ignorar_id)
        return self.db.scalar(consulta)

    def _totais(self):
        alunos = (
            select(func.count())
            .select_from(EbdAluno)
            .outerjoin(Membro, EbdAluno.membro_id == Membro.id)
            .where(EbdAluno.classe_id == EbdClasse.id, EbdAluno.saiu_em.is_(None), _ALUNO_VIVO)
            .correlate(EbdClasse)
            .scalar_subquery()
        )
        professores = (
            select(func.count())
            .select_from(EbdProfessor)
            .join(Membro, EbdProfessor.membro_id == Membro.id)
            .where(
                EbdProfessor.classe_id == EbdClasse.id,
                EbdProfessor.fim.is_(None),
                Membro.excluido_em.is_(None),
            )
            .correlate(EbdClasse)
            .scalar_subquery()
        )
        return alunos, professores

    def list_classes(
        self, igreja_id: uuid.UUID, ids: set[uuid.UUID] | None = None
    ) -> list[tuple[EbdClasse, int, int]]:
        alunos, professores = self._totais()
        consulta = select(EbdClasse, alunos, professores).where(EbdClasse.igreja_id == igreja_id)
        if ids is not None:
            consulta = consulta.where(EbdClasse.id.in_(ids))
        # Ativas primeiro
        consulta = consulta.order_by(EbdClasse.ativa.desc(), EbdClasse.nome)
        return [(c, a, p) for c, a, p in self.db.execute(consulta)]

    def get_classe_com_totais(
        self, igreja_id: uuid.UUID, classe_id: uuid.UUID
    ) -> tuple[EbdClasse, int, int] | None:
        alunos, professores = self._totais()
        linha = self.db.execute(
            select(EbdClasse, alunos, professores).where(
                EbdClasse.id == classe_id, EbdClasse.igreja_id == igreja_id
            )
        ).first()
        return (linha[0], linha[1], linha[2]) if linha else None

    def create_classe(self, igreja_id: uuid.UUID, campos: dict) -> EbdClasse:
        classe = EbdClasse(igreja_id=igreja_id, **campos)
        self.db.add(classe)
        self.db.flush()
        self.db.refresh(classe)  # traz `ativa` (default do banco)
        return classe

    # ---------- professores ----------

    def _professores(self):
        return select(EbdProfessor, Membro.nome).join(
            Membro, EbdProfessor.membro_id == Membro.id
        ).where(Membro.excluido_em.is_(None))

    def list_professores(
        self, igreja_id: uuid.UUID, classe_id: uuid.UUID, incluir_encerrados: bool
    ) -> list[tuple[EbdProfessor, str]]:
        consulta = self._professores().where(
            EbdProfessor.igreja_id == igreja_id, EbdProfessor.classe_id == classe_id
        )
        if not incluir_encerrados:
            consulta = consulta.where(EbdProfessor.fim.is_(None))
        consulta = consulta.order_by(
            EbdProfessor.fim.is_not(None), EbdProfessor.inicio.desc(), Membro.nome, EbdProfessor.id
        )
        return [(p, n) for p, n in self.db.execute(consulta)]

    def get_professor(
        self, igreja_id: uuid.UUID, classe_id: uuid.UUID, professor_id: uuid.UUID
    ) -> tuple[EbdProfessor, str] | None:
        linha = self.db.execute(
            self._professores().where(
                EbdProfessor.id == professor_id,
                EbdProfessor.igreja_id == igreja_id,
                EbdProfessor.classe_id == classe_id,
            )
        ).first()
        return (linha[0], linha[1]) if linha else None

    def professor_ativo(self, classe_id: uuid.UUID, membro_id: uuid.UUID) -> EbdProfessor | None:
        return self.db.scalar(
            select(EbdProfessor).where(
                EbdProfessor.classe_id == classe_id,
                EbdProfessor.membro_id == membro_id,
                EbdProfessor.fim.is_(None),
            )
        )

    def classes_do_professor(self, igreja_id: uuid.UUID, membro_id: uuid.UUID) -> set[uuid.UUID]:
        """Classes em que o membro está em exercício como professor."""
        return set(
            self.db.scalars(
                select(EbdProfessor.classe_id).where(
                    EbdProfessor.igreja_id == igreja_id,
                    EbdProfessor.membro_id == membro_id,
                    EbdProfessor.fim.is_(None),
                )
            )
        )

    def e_professor(self, igreja_id: uuid.UUID, membro_id: uuid.UUID) -> bool:
        """Professor em exercício de alguma classe ativa (público "professores_ebd")."""
        return (
            self.db.scalar(
                select(EbdProfessor.id)
                .join(EbdClasse, EbdClasse.id == EbdProfessor.classe_id)
                .where(
                    EbdProfessor.igreja_id == igreja_id,
                    EbdProfessor.membro_id == membro_id,
                    EbdProfessor.fim.is_(None),
                    EbdClasse.ativa.is_(True),
                )
                .limit(1)
            )
            is not None
        )

    def create_professor(self, igreja_id: uuid.UUID, classe_id: uuid.UUID, campos: dict) -> EbdProfessor:
        professor = EbdProfessor(igreja_id=igreja_id, classe_id=classe_id, **campos)
        self.db.add(professor)
        self.db.flush()
        self.db.refresh(professor)  # traz `inicio` (default do banco)
        return professor

    # ---------- alunos ----------

    def list_alunos(
        self, igreja_id: uuid.UUID, classe_id: uuid.UUID, incluir_ex: bool = False
    ) -> list[tuple[EbdAluno, str]]:
        consulta = (
            select(EbdAluno, _NOME_ALUNO)
            .outerjoin(Membro, EbdAluno.membro_id == Membro.id)
            .where(EbdAluno.igreja_id == igreja_id, EbdAluno.classe_id == classe_id, _ALUNO_VIVO)
            .order_by(_NOME_ALUNO, EbdAluno.id)
        )
        if not incluir_ex:
            consulta = consulta.where(EbdAluno.saiu_em.is_(None))
        return [(a, n) for a, n in self.db.execute(consulta)]

    def get_aluno(
        self, igreja_id: uuid.UUID, classe_id: uuid.UUID, aluno_id: uuid.UUID
    ) -> tuple[EbdAluno, str] | None:
        linha = self.db.execute(
            select(EbdAluno, _NOME_ALUNO)
            .outerjoin(Membro, EbdAluno.membro_id == Membro.id)
            .where(
                EbdAluno.id == aluno_id,
                EbdAluno.igreja_id == igreja_id,
                EbdAluno.classe_id == classe_id,
                _ALUNO_VIVO,
            )
        ).first()
        return (linha[0], linha[1]) if linha else None

    def aluno_ativo_do_membro(self, classe_id: uuid.UUID, membro_id: uuid.UUID) -> EbdAluno | None:
        return self.db.scalar(
            select(EbdAluno).where(
                EbdAluno.classe_id == classe_id,
                EbdAluno.membro_id == membro_id,
                EbdAluno.saiu_em.is_(None),
            )
        )

    def create_aluno(self, igreja_id: uuid.UUID, classe_id: uuid.UUID, campos: dict) -> EbdAluno:
        aluno = EbdAluno(igreja_id=igreja_id, classe_id=classe_id, **campos)
        self.db.add(aluno)
        self.db.flush()
        self.db.refresh(aluno)  # traz `entrou_em` (default do banco)
        return aluno

    # ---------- aulas ----------

    def get_aula(
        self, igreja_id: uuid.UUID, classe_id: uuid.UUID, aula_id: uuid.UUID
    ) -> EbdAula | None:
        return self.db.scalar(
            select(EbdAula).where(
                EbdAula.id == aula_id,
                EbdAula.igreja_id == igreja_id,
                EbdAula.classe_id == classe_id,
            )
        )

    def aula_na_data(
        self, classe_id: uuid.UUID, data: date, ignorar_id: uuid.UUID | None = None
    ) -> bool:
        consulta = select(EbdAula.id).where(EbdAula.classe_id == classe_id, EbdAula.data == data)
        if ignorar_id:
            consulta = consulta.where(EbdAula.id != ignorar_id)
        return self.db.scalar(consulta) is not None

    def create_aula(
        self, igreja_id: uuid.UUID, classe_id: uuid.UUID, data: date, licao: str | None
    ) -> EbdAula:
        aula = EbdAula(igreja_id=igreja_id, classe_id=classe_id, data=data, licao=licao)
        self.db.add(aula)
        self.db.flush()
        return aula

    @staticmethod
    def _contagens():
        def conta(status: StatusPresenca):
            return func.count(EbdPresenca.aluno_id).filter(EbdPresenca.status == status)

        return (
            conta(StatusPresenca.PRESENTE),
            conta(StatusPresenca.AUSENTE),
            conta(StatusPresenca.JUSTIFICADO),
        )

    def list_aulas(
        self, igreja_id: uuid.UUID, classe_id: uuid.UUID
    ) -> list[tuple[EbdAula, int, int, int]]:
        p, a, j = self._contagens()
        linhas = self.db.execute(
            select(EbdAula, p, a, j)
            .outerjoin(EbdPresenca, EbdPresenca.aula_id == EbdAula.id)
            .where(EbdAula.igreja_id == igreja_id, EbdAula.classe_id == classe_id)
            .group_by(EbdAula.id)
            .order_by(EbdAula.data.desc())
        )
        return [(aula, *c) for aula, *c in linhas]

    def contagem_da_aula(self, aula_id: uuid.UUID) -> tuple[int, int, int]:
        p, a, j = self._contagens()
        linha = self.db.execute(select(p, a, j).where(EbdPresenca.aula_id == aula_id)).one()
        return (linha[0], linha[1], linha[2])

    # ---------- presença ----------

    def list_presencas(self, aula_id: uuid.UUID) -> list[tuple[EbdPresenca, str]]:
        linhas = self.db.execute(
            select(EbdPresenca, _NOME_ALUNO)
            .join(EbdAluno, EbdAluno.id == EbdPresenca.aluno_id)
            .outerjoin(Membro, EbdAluno.membro_id == Membro.id)
            .where(EbdPresenca.aula_id == aula_id)
            .order_by(_NOME_ALUNO, EbdAluno.id)
        )
        return [(p, n) for p, n in linhas]

    def upsert_presencas(
        self, igreja_id: uuid.UUID, aula_id: uuid.UUID, itens: dict[uuid.UUID, StatusPresenca]
    ) -> None:
        existentes = {
            p.aluno_id: p
            for p in self.db.scalars(select(EbdPresenca).where(EbdPresenca.aula_id == aula_id))
        }
        for aluno_id, status in itens.items():
            if aluno_id in existentes:
                existentes[aluno_id].status = status
            else:
                self.db.add(
                    EbdPresenca(
                        igreja_id=igreja_id, aula_id=aula_id, aluno_id=aluno_id, status=status
                    )
                )
        self.db.flush()

    # ---------- frequência ----------

    def total_aulas(self, classe_id: uuid.UUID, de: date | None, ate: date | None) -> int:
        consulta = select(func.count()).select_from(EbdAula).where(EbdAula.classe_id == classe_id)
        if de:
            consulta = consulta.where(EbdAula.data >= de)
        if ate:
            consulta = consulta.where(EbdAula.data <= ate)
        return self.db.scalar(consulta) or 0

    def contagem_por_aluno(
        self, classe_id: uuid.UUID, de: date | None, ate: date | None
    ) -> dict[uuid.UUID, dict[StatusPresenca, int]]:
        consulta = (
            select(EbdPresenca.aluno_id, EbdPresenca.status, func.count())
            .join(EbdAula, EbdAula.id == EbdPresenca.aula_id)
            .where(EbdAula.classe_id == classe_id)
            .group_by(EbdPresenca.aluno_id, EbdPresenca.status)
        )
        if de:
            consulta = consulta.where(EbdAula.data >= de)
        if ate:
            consulta = consulta.where(EbdAula.data <= ate)
        saida: dict[uuid.UUID, dict[StatusPresenca, int]] = {}
        for aluno_id, status, n in self.db.execute(consulta):
            saida.setdefault(aluno_id, {})[status] = n
        return saida
