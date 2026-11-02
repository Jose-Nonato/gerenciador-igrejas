import uuid
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from models import Lideranca, Reuniao, Socio, Sociedade, Usuario
from models.enums import (
    CARGOS_UNICOS,
    CargoLideranca,
    PerfilUsuario,
    SituacaoMembro,
    StatusPresenca,
    TipoSocio,
)
from repositories import (
    AuditoriaRepository,
    LiderancaRepository,
    MembroRepository,
    SociedadeRepository,
)
from schemas import (
    LiderancaCreate,
    LiderancaUpdate,
    PresencaItem,
    ReuniaoCreate,
    ReuniaoUpdate,
    SocioCreate,
    SocioUpdate,
    SociedadeCreate,
    SociedadeUpdate,
)

_NOME_CARGO = {
    CargoLideranca.PRESIDENTE: "presidente",
    CargoLideranca.VICE_PRESIDENTE: "vice-presidente",
    CargoLideranca.SECRETARIO: "secretário",
    CargoLideranca.TESOUREIRO: "tesoureiro",
    CargoLideranca.CONSELHEIRO: "conselheiro",
    CargoLideranca.OUTRO: "este cargo",
}

# Quem já saiu do rol não pode ser sócio nem líder
_FORA_DO_ROL = {SituacaoMembro.TRANSFERIDO, SituacaoMembro.FALECIDO, SituacaoMembro.EXCLUIDO}


class SociedadeController:
    """Sociedades internas.

    Admin e pastor acessam todas. Quem tem um mandato em exercício na diretoria de uma
    sociedade (qualquer cargo) vê e edita só a dela, exceto o que é de gestor: criar
    sociedade, mudar o nome e alterar a diretoria. A autorização está em `get`, pelo qual
    passa toda operação por sociedade.
    """

    def __init__(
        self,
        sociedades: SociedadeRepository,
        membros: MembroRepository,
        audit: AuditoriaRepository,
        db: Session,
        lideranca: LiderancaRepository,
    ) -> None:
        self.sociedades = sociedades
        self.lideranca = lideranca
        self.membros = membros
        self.audit = audit
        self.db = db

    # ---------- sociedade ----------

    @staticmethod
    def _e_gestor(ator: Usuario) -> bool:
        return ator.perfil in (PerfilUsuario.ADMIN, PerfilUsuario.PASTOR)

    def _sociedades_do_ator(self, ator: Usuario) -> set[uuid.UUID]:
        if ator.membro_id is None:
            return set()
        return self.lideranca.sociedades_lideradas(ator.igreja_id, ator.membro_id)

    def listar(self, ator: Usuario) -> list[tuple[Sociedade, int]]:
        if self._e_gestor(ator):
            return self.sociedades.list_with_totals(ator.igreja_id)
        return self.sociedades.list_with_totals(ator.igreja_id, ids=self._sociedades_do_ator(ator))

    def get(
        self, ator: Usuario, sociedade_id: uuid.UUID, *, so_gestor: bool = False
    ) -> Sociedade:
        # Sempre filtrado pela igreja do ator: outra igreja aparece como inexistente
        sociedade = self.sociedades.get(ator.igreja_id, sociedade_id)
        if sociedade is None:
            raise NotFoundError("Sociedade não encontrada")
        if not self._e_gestor(ator):
            if so_gestor:
                raise ForbiddenError("Apenas administrador e pastor podem fazer isso")
            if sociedade.id not in self._sociedades_do_ator(ator):
                raise ForbiddenError("Você não faz parte da liderança desta sociedade")
        return sociedade

    def get_com_total(self, ator: Usuario, sociedade_id: uuid.UUID) -> tuple[Sociedade, int]:
        sociedade = self.get(ator, sociedade_id)
        return sociedade, self.sociedades.total_socios(sociedade.id)

    def criar(self, ator: Usuario, data: SociedadeCreate) -> tuple[Sociedade, int]:
        if self.sociedades.get_by_sigla(ator.igreja_id, data.sigla):
            raise ConflictError(f"Já existe uma sociedade {data.sigla.value}")
        sociedade = self.sociedades.create(ator.igreja_id, data.sigla, _limpo(data.nome))
        self.audit.registrar(
            ator.igreja_id, ator.id, "sociedade_criada", "sociedade", sociedade.id,
            {"sigla": data.sigla.value}, commit=False,
        )
        self._commit("Já existe uma sociedade com esta sigla")
        return sociedade, 0

    def atualizar(
        self, ator: Usuario, sociedade_id: uuid.UUID, data: SociedadeUpdate
    ) -> tuple[Sociedade, int]:
        sociedade = self.get(ator, sociedade_id, so_gestor=True)
        self.sociedades.apply(sociedade, {"nome": _limpo(data.nome)})
        self._commit()
        return sociedade, self.sociedades.total_socios(sociedade.id)

    # ---------- busca de membros para o cadastro de sócios ----------

    def buscar_membros(self, ator: Usuario, sociedade_id: uuid.UUID, q: str) -> list:
        """Busca por nome só com o necessário (nome e nº do rol), para quem lidera a sociedade
        poder cadastrar sócios sem ter acesso ao rol completo. Só quem ainda faz parte do rol."""
        self.get(ator, sociedade_id)
        return self.membros.buscar_elegiveis(ator.igreja_id, q, limit=10)

    # ---------- sócios ----------

    def listar_socios(
        self, ator: Usuario, sociedade_id: uuid.UUID, incluir_ex: bool
    ) -> list[tuple[Socio, str]]:
        self.get(ator, sociedade_id)
        return self.sociedades.list_socios(ator.igreja_id, sociedade_id, incluir_ex)

    def adicionar_socio(
        self, ator: Usuario, sociedade_id: uuid.UUID, data: SocioCreate
    ) -> tuple[Socio, str]:
        sociedade = self.get(ator, sociedade_id)
        nome = data.nome_externo
        if data.membro_id is not None:
            membro = self.membros.get_in_church(ator.igreja_id, data.membro_id)
            if membro is None:
                raise NotFoundError("Membro não encontrado")
            if membro.situacao in _FORA_DO_ROL:
                raise ConflictError("Este membro não faz mais parte do rol")
            if self.sociedades.socio_ativo_do_membro(sociedade.id, membro.id):
                raise ConflictError("Este membro já é sócio desta sociedade")
            nome = membro.nome

        socio = self.sociedades.create_socio(
            ator.igreja_id,
            sociedade.id,
            {"tipo": data.tipo, "membro_id": data.membro_id, "nome_externo": data.nome_externo},
        )
        self.audit.registrar(
            ator.igreja_id, ator.id, "socio_adicionado", "socio", socio.id,
            {"sociedade": sociedade.sigla.value, "tipo": data.tipo.value, "nome": nome},
            commit=False,
        )
        self._commit("Este membro já é sócio desta sociedade")
        return socio, nome or ""

    def atualizar_socio(
        self, ator: Usuario, sociedade_id: uuid.UUID, socio_id: uuid.UUID, data: SocioUpdate
    ) -> tuple[Socio, str]:
        socio, nome = self._get_socio(ator, sociedade_id, socio_id)
        if socio.saiu_em is not None:
            raise ConflictError("Sócio que já saiu não pode ser alterado")

        campos: dict = {}
        if data.tipo is not None and data.tipo != socio.tipo:
            # Trocar para/de não membro muda a identidade do sócio: remova e cadastre de novo
            if (data.tipo == TipoSocio.NAO_MEMBRO) != (socio.tipo == TipoSocio.NAO_MEMBRO):
                raise AppError("Não é possível converter entre membro e não membro")
            campos["tipo"] = data.tipo
        if data.nome_externo is not None:
            if socio.tipo != TipoSocio.NAO_MEMBRO:
                raise AppError("O nome só pode ser alterado para não membros")
            nome = data.nome_externo.strip()
            if not nome:
                raise AppError("Informe o nome")
            campos["nome_externo"] = nome

        if campos:
            self.sociedades.apply(socio, campos)
            self.audit.registrar(
                ator.igreja_id, ator.id, "socio_alterado", "socio", socio.id,
                {k: (v.value if hasattr(v, "value") else v) for k, v in campos.items()},
                commit=False,
            )
            self._commit()
        return socio, nome

    def remover_socio(
        self, ator: Usuario, sociedade_id: uuid.UUID, socio_id: uuid.UUID
    ) -> None:
        """O sócio sai da sociedade (data de saída); a presença histórica é mantida."""
        socio, nome = self._get_socio(ator, sociedade_id, socio_id)
        if socio.saiu_em is not None:
            raise ConflictError("Este sócio já saiu da sociedade")
        self.sociedades.apply(socio, {"saiu_em": date.today()})
        self.audit.registrar(
            ator.igreja_id, ator.id, "socio_removido", "socio", socio.id,
            {"nome": nome}, commit=False,
        )
        self._commit()

    # ---------- reuniões ----------

    def listar_reunioes(
        self, ator: Usuario, sociedade_id: uuid.UUID
    ) -> list[tuple[Reuniao, int, int, int]]:
        self.get(ator, sociedade_id)
        return self.sociedades.list_reunioes(ator.igreja_id, sociedade_id)

    def criar_reuniao(
        self, ator: Usuario, sociedade_id: uuid.UUID, data: ReuniaoCreate
    ) -> Reuniao:
        sociedade = self.get(ator, sociedade_id)
        if self.sociedades.reuniao_na_data(sociedade.id, data.data):
            raise ConflictError("Já existe uma reunião nesta data")
        # Valida tudo antes de gravar qualquer coisa
        itens = self._validar_presencas(ator, sociedade.id, data.data, data.presencas)

        reuniao = self.sociedades.create_reuniao(
            ator.igreja_id, sociedade.id, data.data, _limpo(data.tema)
        )
        if itens:
            self.sociedades.upsert_presencas(ator.igreja_id, reuniao.id, itens)
        self.audit.registrar(
            ator.igreja_id, ator.id, "reuniao_criada", "reuniao", reuniao.id,
            {"sociedade": sociedade.sigla.value, "data": data.data.isoformat(),
             "presencas": len(itens)},
            commit=False,
        )
        self._commit("Já existe uma reunião nesta data")
        return reuniao

    def atualizar_reuniao(
        self, ator: Usuario, sociedade_id: uuid.UUID, reuniao_id: uuid.UUID, data: ReuniaoUpdate
    ) -> Reuniao:
        reuniao = self._get_reuniao(ator, sociedade_id, reuniao_id)
        campos: dict = {}
        if data.data is not None and data.data != reuniao.data:
            if self.sociedades.reuniao_na_data(sociedade_id, data.data, ignorar_id=reuniao.id):
                raise ConflictError("Já existe uma reunião nesta data")
            campos["data"] = data.data
        if "tema" in data.model_fields_set:
            campos["tema"] = _limpo(data.tema)
        if campos:
            self.sociedades.apply(reuniao, campos)
            self._commit("Já existe uma reunião nesta data")
        return reuniao

    def contagem(self, reuniao_id: uuid.UUID) -> tuple[int, int, int]:
        return self.sociedades.contagem_da_reuniao(reuniao_id)

    def detalhe_reuniao(
        self, ator: Usuario, sociedade_id: uuid.UUID, reuniao_id: uuid.UUID
    ) -> tuple[Reuniao, list]:
        reuniao = self._get_reuniao(ator, sociedade_id, reuniao_id)
        return reuniao, self.sociedades.list_presencas(reuniao.id)

    def lancar_presencas(
        self,
        ator: Usuario,
        sociedade_id: uuid.UUID,
        reuniao_id: uuid.UUID,
        presencas: list[PresencaItem],
    ) -> Reuniao:
        """Lançamento em lote: cria ou corrige a presença de cada sócio informado."""
        reuniao = self._get_reuniao(ator, sociedade_id, reuniao_id)
        itens = self._validar_presencas(ator, sociedade_id, reuniao.data, presencas)
        if itens:
            self.sociedades.upsert_presencas(ator.igreja_id, reuniao.id, itens)
            self.audit.registrar(
                ator.igreja_id, ator.id, "presencas_lancadas", "reuniao", reuniao.id,
                {"registros": len(itens)}, commit=False,
            )
            self._commit()
        return reuniao

    # ---------- frequência ----------

    def frequencia(
        self, ator: Usuario, sociedade_id: uuid.UUID, de: date | None, ate: date | None
    ) -> dict:
        self.get(ator, sociedade_id)
        if de and ate and de > ate:
            raise AppError("A data inicial não pode ser depois da final")

        total = self.sociedades.total_reunioes(sociedade_id, de, ate)
        por_socio = self.sociedades.contagem_por_socio(sociedade_id, de, ate)
        linhas = []
        for socio, nome in self.sociedades.list_socios(ator.igreja_id, sociedade_id, incluir_ex=True):
            c = por_socio.get(socio.id, {})
            p = c.get(StatusPresenca.PRESENTE, 0)
            a = c.get(StatusPresenca.AUSENTE, 0)
            j = c.get(StatusPresenca.JUSTIFICADO, 0)
            registrados = p + a + j
            # Quem já saiu só aparece se tiver presença no período
            if socio.saiu_em is not None and registrados == 0:
                continue
            linhas.append(
                {
                    "socio_id": socio.id,
                    "nome": nome,
                    "tipo": socio.tipo,
                    "presentes": p,
                    "ausentes": a,
                    "justificados": j,
                    "sem_registro": max(total - registrados, 0),
                    "percentual_presenca": round(100 * p / registrados, 1) if registrados else None,
                }
            )
        return {"de": de, "ate": ate, "total_reunioes": total, "socios": linhas}

    # ---------- liderança (diretoria) ----------

    def listar_lideranca(
        self, ator: Usuario, sociedade_id: uuid.UUID, incluir_encerrados: bool
    ) -> list[tuple[Lideranca, str]]:
        self.get(ator, sociedade_id)
        return self.lideranca.list(ator.igreja_id, sociedade_id, incluir_encerrados)

    def adicionar_lideranca(
        self, ator: Usuario, sociedade_id: uuid.UUID, data: LiderancaCreate
    ) -> tuple[Lideranca, str]:
        sociedade = self.get(ator, sociedade_id, so_gestor=True)
        membro = self.membros.get_in_church(ator.igreja_id, data.membro_id)
        if membro is None:
            raise NotFoundError("Membro não encontrado")
        if membro.situacao in _FORA_DO_ROL:
            raise ConflictError("Este membro não faz mais parte do rol")

        if data.cargo in CARGOS_UNICOS:
            if self.lideranca.ocupante_ativo(sociedade.id, data.cargo):
                raise ConflictError(
                    f"Já há {_NOME_CARGO[data.cargo]} em exercício: encerre o mandato atual antes"
                )
        elif self.lideranca.membro_no_cargo(
            sociedade.id, membro.id, data.cargo, data.cargo_descricao
        ):
            raise ConflictError("Este membro já exerce este cargo")

        campos = {
            "membro_id": membro.id,
            "cargo": data.cargo,
            "cargo_descricao": data.cargo_descricao,
        }
        if data.inicio is not None:
            campos["inicio"] = data.inicio
        item = self.lideranca.create(ator.igreja_id, sociedade.id, campos)
        self.audit.registrar(
            ator.igreja_id, ator.id, "lideranca_adicionada", "lideranca", item.id,
            {"sociedade": sociedade.sigla.value, "cargo": data.cargo.value, "nome": membro.nome},
            commit=False,
        )
        self._commit("Já há alguém neste cargo em exercício")
        return item, membro.nome

    def atualizar_lideranca(
        self,
        ator: Usuario,
        sociedade_id: uuid.UUID,
        lideranca_id: uuid.UUID,
        data: LiderancaUpdate,
    ) -> tuple[Lideranca, str]:
        self.get(ator, sociedade_id, so_gestor=True)
        achado = self.lideranca.get(ator.igreja_id, sociedade_id, lideranca_id)
        if achado is None:
            raise NotFoundError("Registro de liderança não encontrado")
        item, nome = achado

        inicio = data.inicio or item.inicio
        fim = data.fim if data.fim is not None else item.fim
        if fim is not None and fim < inicio:
            raise AppError("O fim do mandato não pode ser antes do início")

        encerrando = item.fim is None and data.fim is not None
        campos = {}
        if data.inicio is not None:
            campos["inicio"] = data.inicio
        if data.fim is not None:
            campos["fim"] = data.fim
        self.lideranca.apply(item, campos)
        self.audit.registrar(
            ator.igreja_id, ator.id,
            "lideranca_encerrada" if encerrando else "lideranca_alterada",
            "lideranca", item.id,
            {"nome": nome, "cargo": item.cargo.value,
             **{k: v.isoformat() for k, v in campos.items()}},
            commit=False,
        )
        self._commit()
        return item, nome

    # ---------- internos ----------

    def _get_socio(
        self, ator: Usuario, sociedade_id: uuid.UUID, socio_id: uuid.UUID
    ) -> tuple[Socio, str]:
        self.get(ator, sociedade_id)
        achado = self.sociedades.get_socio(ator.igreja_id, sociedade_id, socio_id)
        if achado is None:
            raise NotFoundError("Sócio não encontrado")
        return achado

    def _get_reuniao(
        self, ator: Usuario, sociedade_id: uuid.UUID, reuniao_id: uuid.UUID
    ) -> Reuniao:
        self.get(ator, sociedade_id)
        reuniao = self.sociedades.get_reuniao(ator.igreja_id, sociedade_id, reuniao_id)
        if reuniao is None:
            raise NotFoundError("Reunião não encontrada")
        return reuniao

    def _validar_presencas(
        self,
        ator: Usuario,
        sociedade_id: uuid.UUID,
        data_reuniao: date,
        presencas: list[PresencaItem],
    ) -> dict[uuid.UUID, StatusPresenca]:
        itens: dict[uuid.UUID, StatusPresenca] = {}
        for item in presencas:
            achado = self.sociedades.get_socio(ator.igreja_id, sociedade_id, item.socio_id)
            if achado is None:
                raise NotFoundError("Sócio não encontrado nesta sociedade")
            socio, nome = achado
            if socio.saiu_em is not None and socio.saiu_em < data_reuniao:
                raise ConflictError(f"{nome} já havia saído da sociedade nesta data")
            itens[socio.id] = item.status
        return itens

    def _commit(self, mensagem_conflito: str = "Registro duplicado") -> None:
        try:
            self.db.commit()
        except IntegrityError:
            # Corrida entre duas requisições iguais: a restrição única do banco decide
            self.db.rollback()
            raise ConflictError(mensagem_conflito)


def _limpo(texto: str | None) -> str | None:
    if texto is None:
        return None
    texto = texto.strip()
    return texto or None
