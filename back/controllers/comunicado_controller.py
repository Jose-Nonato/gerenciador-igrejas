import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core import armazenamento
from core.config import settings
from core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from models import Comunicado, Usuario
from models.enums import (
    CategoriaPost,
    Oficio,
    PerfilUsuario,
    Rol,
    SituacaoMembro,
    StatusPost,
    TipoPublico,
)
from repositories import (
    AuditoriaRepository,
    AudienciaLeitor,
    ComunicadoRepository,
    LiderancaRepository,
    MembroRepository,
    SociedadeRepository,
    esta_publicado,
)
from repositories.comunicado_repository import Linha
from schemas import ComunicadoCreate, ComunicadoUpdate, PublicarRequest

_NO_ROL = {SituacaoMembro.ATIVO, SituacaoMembro.EM_DISCIPLINA}


class ComunicadoController:
    """Mural de comunicados.

    Escrever: admin e pastor, para qualquer público; quem está na diretoria de uma sociedade,
    só para essa sociedade. Ler: cada pessoa vê o que está publicado para o público dela.
    """

    def __init__(
        self,
        comunicados: ComunicadoRepository,
        sociedades: SociedadeRepository,
        lideranca: LiderancaRepository,
        membros: MembroRepository,
        audit: AuditoriaRepository,
        db: Session,
    ) -> None:
        self.comunicados = comunicados
        self.sociedades = sociedades
        self.lideranca = lideranca
        self.membros = membros
        self.audit = audit
        self.db = db

    # ---------- quem é quem ----------

    @staticmethod
    def _e_gestor(ator: Usuario) -> bool:
        return ator.perfil in (PerfilUsuario.ADMIN, PerfilUsuario.PASTOR)

    def _lideradas(self, ator: Usuario) -> frozenset[uuid.UUID]:
        if ator.membro_id is None:
            return frozenset()
        return frozenset(self.lideranca.sociedades_lideradas(ator.igreja_id, ator.membro_id))

    def pode_escrever(self, ator: Usuario) -> bool:
        return self._e_gestor(ator) or bool(self._lideradas(ator))

    def _audiencia(self, ator: Usuario) -> AudienciaLeitor:
        if self._e_gestor(ator):
            return AudienciaLeitor(ve_tudo=True)
        membro = (
            self.membros.get_in_church(ator.igreja_id, ator.membro_id) if ator.membro_id else None
        )
        no_rol = membro is not None and membro.situacao in _NO_ROL
        sociedades = set(self._lideradas(ator))
        if membro is not None:
            sociedades |= self.sociedades.sociedades_do_socio(ator.igreja_id, membro.id)
        return AudienciaLeitor(
            comungante=no_rol and membro.rol == Rol.COMUNGANTE,
            # Presbítero (perfil) ou quem foi ordenado presbítero/diácono
            oficial=ator.perfil == PerfilUsuario.PRESBITERO
            or (no_rol and membro.oficio != Oficio.NENHUM),
            sociedades=frozenset(sociedades),
        )

    def _pode_gerir(self, ator: Usuario, publico: TipoPublico, sociedade_id: uuid.UUID | None) -> bool:
        if self._e_gestor(ator):
            return True
        return publico == TipoPublico.SOCIEDADE and sociedade_id in self._lideradas(ator)

    # ---------- leitura ----------

    def mural(
        self, ator: Usuario, categoria: CategoriaPost | None, limit: int, offset: int
    ) -> tuple[list[Linha], int]:
        agora = datetime.now(timezone.utc)
        return self.comunicados.mural(
            ator.igreja_id, self._audiencia(ator), agora, categoria, limit, offset
        )

    def gerenciar(
        self, ator: Usuario, status: StatusPost | None, categoria: CategoriaPost | None,
        limit: int, offset: int,
    ) -> tuple[list[Linha], int]:
        if not self.pode_escrever(ator):
            raise ForbiddenError("Sem permissão para gerenciar comunicados")
        agora = datetime.now(timezone.utc)
        restricao = None if self._e_gestor(ator) else self._lideradas(ator)
        return self.comunicados.gerenciar(
            ator.igreja_id, agora, restricao, status, categoria, limit, offset
        )

    def get(self, ator: Usuario, comunicado_id: uuid.UUID) -> Linha:
        """Quem gerencia o comunicado o vê em qualquer estado; os demais, só se estiver
        publicado para o público deles. Do contrário aparece como inexistente."""
        linha = self.comunicados.get(ator.igreja_id, comunicado_id)
        if linha is None:
            raise NotFoundError("Comunicado não encontrado")
        c = linha[0]
        if self._pode_gerir(ator, c.publico, c.sociedade_id):
            return linha
        agora = datetime.now(timezone.utc)
        if esta_publicado(c, agora) and self._audiencia(ator).permite(c.publico, c.sociedade_id):
            return linha
        raise NotFoundError("Comunicado não encontrado")

    # ---------- escrita ----------

    def criar(self, ator: Usuario, data: ComunicadoCreate) -> Linha:
        if not self._pode_gerir(ator, data.publico, data.sociedade_id):
            raise ForbiddenError(self._mensagem_sem_permissao(ator))
        self._validar_sociedade(ator, data.sociedade_id)

        comunicado = self.comunicados.create(
            ator.igreja_id,
            {**data.model_dump(), "status": StatusPost.RASCUNHO, "autor_id": ator.id},
        )
        self._auditar(ator, "comunicado_criado", comunicado, {"categoria": data.categoria.value})
        self.db.commit()
        return self._reler(ator, comunicado.id)

    def atualizar(self, ator: Usuario, comunicado_id: uuid.UUID, data: ComunicadoUpdate) -> Linha:
        comunicado = self._gerivel(ator, comunicado_id)

        campos = data.model_dump(exclude_unset=True)
        publico = campos.get("publico", comunicado.publico)
        if publico == TipoPublico.SOCIEDADE:
            sociedade_id = campos.get("sociedade_id", comunicado.sociedade_id)
            if sociedade_id is None:
                raise AppError("Informe a sociedade (sociedade_id)")
        else:
            sociedade_id = None
        campos["publico"], campos["sociedade_id"] = publico, sociedade_id

        # O destino novo também precisa ser permitido (o líder não muda o público para a igreja toda)
        if not self._pode_gerir(ator, publico, sociedade_id):
            raise ForbiddenError(self._mensagem_sem_permissao(ator))
        self._validar_sociedade(ator, sociedade_id)

        self.comunicados.apply(comunicado, campos)
        self._auditar(ator, "comunicado_alterado", comunicado, {"campos": sorted(data.model_fields_set)})
        self.db.commit()
        return self._reler(ator, comunicado.id)

    def publicar(self, ator: Usuario, comunicado_id: uuid.UUID, data: PublicarRequest) -> Linha:
        comunicado = self._gerivel(ator, comunicado_id)
        agora = datetime.now(timezone.utc)
        if esta_publicado(comunicado, agora):
            raise ConflictError("Este comunicado já está publicado")

        quando = data.quando
        if quando is not None and quando.tzinfo is None:
            quando = quando.replace(tzinfo=timezone.utc)

        if quando is None or quando <= agora:
            self.comunicados.apply(
                comunicado,
                {"status": StatusPost.PUBLICADO, "publicado_em": agora, "publicar_em": None},
            )
            acao, detalhes = "comunicado_publicado", {}
        else:
            self.comunicados.apply(
                comunicado,
                {"status": StatusPost.AGENDADO, "publicar_em": quando, "publicado_em": None},
            )
            acao, detalhes = "comunicado_agendado", {"para": quando.isoformat()}
        self._auditar(ator, acao, comunicado, detalhes)
        self.db.commit()
        return self._reler(ator, comunicado.id)

    def despublicar(self, ator: Usuario, comunicado_id: uuid.UUID) -> Linha:
        """Volta para rascunho (também cancela um agendamento)."""
        comunicado = self._gerivel(ator, comunicado_id)
        if comunicado.status == StatusPost.RASCUNHO:
            raise ConflictError("Este comunicado já é um rascunho")
        self.comunicados.apply(
            comunicado,
            {"status": StatusPost.RASCUNHO, "publicar_em": None, "publicado_em": None},
        )
        self._auditar(ator, "comunicado_despublicado", comunicado, {})
        self.db.commit()
        return self._reler(ator, comunicado.id)

    def excluir(self, ator: Usuario, comunicado_id: uuid.UUID) -> None:
        """Exclusão lógica: some do mural e da gestão; a linha e a auditoria permanecem."""
        comunicado = self._gerivel(ator, comunicado_id)
        self.comunicados.apply(comunicado, {"excluido_em": datetime.now(timezone.utc)})
        self._auditar(ator, "comunicado_excluido", comunicado, {"titulo": comunicado.titulo})
        self.db.commit()

    # ---------- imagem ----------

    def definir_imagem(self, ator: Usuario, comunicado_id: uuid.UUID, dados: bytes) -> Linha:
        comunicado = self._gerivel(ator, comunicado_id)
        limite = settings.MAX_IMAGEM_MB * 1024 * 1024
        if not dados:
            raise AppError("Arquivo vazio")
        if len(dados) > limite:
            raise AppError(f"A imagem passa de {settings.MAX_IMAGEM_MB} MB")
        extensao = armazenamento.detectar_extensao(dados)
        if extensao is None:
            raise AppError("Formato não aceito. Envie uma imagem JPEG, PNG, GIF ou WebP")

        antiga = comunicado.imagem
        novo = armazenamento.salvar(dados, extensao)
        try:
            self.comunicados.apply(comunicado, {"imagem": novo})
            self._auditar(ator, "comunicado_imagem_definida", comunicado, {})
            self.db.commit()
        except Exception:
            self.db.rollback()
            armazenamento.remover(novo)
            raise
        armazenamento.remover(antiga)
        return self._reler(ator, comunicado.id)

    def remover_imagem(self, ator: Usuario, comunicado_id: uuid.UUID) -> Linha:
        comunicado = self._gerivel(ator, comunicado_id)
        antiga = comunicado.imagem
        if antiga is None:
            raise NotFoundError("Este comunicado não tem imagem")
        self.comunicados.apply(comunicado, {"imagem": None})
        self._auditar(ator, "comunicado_imagem_removida", comunicado, {})
        self.db.commit()
        armazenamento.remover(antiga)
        return self._reler(ator, comunicado.id)

    def obter_imagem(self, ator: Usuario, comunicado_id: uuid.UUID):
        """Arquivo da imagem; vale a mesma regra de visibilidade do comunicado."""
        c = self.get(ator, comunicado_id)[0]
        arquivo = armazenamento.caminho(c.imagem) if c.imagem else None
        if arquivo is None:
            raise NotFoundError("Este comunicado não tem imagem")
        return arquivo, armazenamento.media_type(c.imagem)

    # ---------- internos ----------

    def _gerivel(self, ator: Usuario, comunicado_id: uuid.UUID) -> Comunicado:
        linha = self.comunicados.get(ator.igreja_id, comunicado_id)
        if linha is None:
            raise NotFoundError("Comunicado não encontrado")
        c = linha[0]
        if not self._pode_gerir(ator, c.publico, c.sociedade_id):
            # Quem só lê não deve saber que o rascunho existe
            if self._audiencia(ator).permite(c.publico, c.sociedade_id) and esta_publicado(
                c, datetime.now(timezone.utc)
            ):
                raise ForbiddenError(self._mensagem_sem_permissao(ator))
            raise NotFoundError("Comunicado não encontrado")
        return c

    def _validar_sociedade(self, ator: Usuario, sociedade_id: uuid.UUID | None) -> None:
        if sociedade_id is not None and self.sociedades.get(ator.igreja_id, sociedade_id) is None:
            raise NotFoundError("Sociedade não encontrada")

    def _reler(self, ator: Usuario, comunicado_id: uuid.UUID) -> Linha:
        self.db.expire_all()
        linha = self.comunicados.get(ator.igreja_id, comunicado_id)
        assert linha is not None
        return linha

    def _auditar(self, ator: Usuario, acao: str, c: Comunicado, detalhes: dict) -> None:
        self.audit.registrar(
            ator.igreja_id, ator.id, acao, "comunicado", c.id,
            {"titulo": c.titulo, "publico": c.publico.value, **detalhes},
            commit=False,
        )

    def _mensagem_sem_permissao(self, ator: Usuario) -> str:
        if self._lideradas(ator):
            return "Você só pode publicar comunicados para a sua própria sociedade"
        return "Apenas administrador, pastor e a liderança de uma sociedade escrevem comunicados"
