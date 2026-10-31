import csv
import io
import uuid
from enum import Enum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from controllers.regras_rol import calcular_efeitos
from core.exceptions import ConflictError, NotFoundError
from models import EventoEclesiastico, Membro, Usuario
from repositories import (
    AuditoriaRepository,
    EventoRepository,
    FamiliaRepository,
    MembroRepository,
)
from schemas import EventoCreate, FiltroMembros, MembroCreate, MembroUpdate

_COLUNAS_CSV = [
    "numero_rol", "nome", "rol", "situacao", "oficio", "data_nascimento",
    "sexo", "estado_civil", "telefone", "email", "endereco",
]


def _valor(v):
    return v.value if isinstance(v, Enum) else v


class MembroController:
    def __init__(
        self,
        membros: MembroRepository,
        familias: FamiliaRepository,
        eventos: EventoRepository,
        audit: AuditoriaRepository,
        db: Session,
    ) -> None:
        self.membros = membros
        self.familias = familias
        self.eventos = eventos
        self.audit = audit
        self.db = db

    # ---------- consulta ----------

    def get(self, ator: Usuario, membro_id: uuid.UUID) -> Membro:
        # Sempre filtrado pela igreja do ator: outra igreja aparece como inexistente
        membro = self.membros.get_in_church(ator.igreja_id, membro_id)
        if membro is None:
            raise NotFoundError("Membro não encontrado")
        return membro

    def get_meu(self, ator: Usuario) -> Membro:
        if ator.membro_id is None:
            raise NotFoundError("Seu usuário não está vinculado a um membro")
        return self.get(ator, ator.membro_id)

    def buscar(self, ator: Usuario, filtro: FiltroMembros) -> tuple[list[Membro], int]:
        return self.membros.search(ator.igreja_id, **filtro.model_dump())

    def eventos_do_membro(self, ator: Usuario, membro_id: uuid.UUID) -> list[EventoEclesiastico]:
        self.get(ator, membro_id)
        return self.eventos.list_by_membro(ator.igreja_id, membro_id)

    def exportar_csv(self, ator: Usuario, filtro: FiltroMembros) -> str:
        dados = filtro.model_dump(exclude={"limit", "offset"})
        membros, _ = self.membros.search(ator.igreja_id, **dados)
        self.audit.registrar(
            ator.igreja_id, ator.id, "rol_exportado", "membro", None, {"registros": len(membros)}
        )

        saida = io.StringIO()
        saida.write("﻿")  # BOM: o Excel abre em UTF-8
        writer = csv.writer(saida, delimiter=";")
        writer.writerow(_COLUNAS_CSV)
        for m in membros:
            writer.writerow([_seguro_csv(_valor(getattr(m, c))) for c in _COLUNAS_CSV])
        return saida.getvalue()

    # ---------- escrita ----------

    def criar(self, ator: Usuario, data: MembroCreate) -> Membro:
        campos = data.model_dump(exclude={"numero_rol"})
        if data.email:
            campos["email"] = data.email.lower()
        self._validar_familia(ator, data.familia_id)
        if data.numero_rol is not None and self.membros.numero_rol_em_uso(
            ator.igreja_id, data.numero_rol
        ):
            raise ConflictError("Número do rol já em uso")

        membro = self.membros.create(ator.igreja_id, campos, data.numero_rol)
        self.audit.registrar(
            ator.igreja_id, ator.id, "membro_criado", "membro", membro.id,
            {"nome": membro.nome, "numero_rol": membro.numero_rol, "rol": membro.rol.value},
            commit=False,
        )
        self._commit()
        self.db.refresh(membro)
        return membro

    def atualizar(self, ator: Usuario, membro_id: uuid.UUID, data: MembroUpdate) -> Membro:
        membro = self.get(ator, membro_id)
        campos = data.model_dump(exclude_unset=True)
        if campos.get("nome", "") is None:
            campos.pop("nome")  # obrigatório; null explícito é ignorado
        if campos.get("email"):
            campos["email"] = campos["email"].lower()
        if campos.get("familia_id"):
            self._validar_familia(ator, campos["familia_id"])

        numero_antes = membro.numero_rol
        novo_numero = campos.get("numero_rol")
        if "numero_rol" in campos and novo_numero is None:
            campos.pop("numero_rol")  # o número do rol não pode ser removido
        elif novo_numero is not None and novo_numero != numero_antes:
            if self.membros.numero_rol_em_uso(ator.igreja_id, novo_numero, ignorar_id=membro.id):
                raise ConflictError("Número do rol já em uso")

        self.membros.apply(membro, campos)
        if "numero_rol" in campos and campos["numero_rol"] != numero_antes:
            self.audit.registrar(
                ator.igreja_id, ator.id, "numero_rol_alterado", "membro", membro.id,
                {"de": numero_antes, "para": campos["numero_rol"]},
                commit=False,
            )
        self._commit()
        self.db.refresh(membro)
        return membro

    def registrar_evento(
        self, ator: Usuario, membro_id: uuid.UUID, data: EventoCreate
    ) -> tuple[EventoEclesiastico, Membro]:
        """Grava o evento, aplica seus efeitos ao membro e audita, tudo numa transação."""
        membro = self.get(ator, membro_id)
        efeitos = calcular_efeitos(membro, data)

        evento = self.eventos.create(ator.igreja_id, membro.id, data.model_dump())
        alteracoes = {
            campo: {"de": _valor(getattr(membro, campo)), "para": _valor(novo)}
            for campo, novo in efeitos.items()
            if getattr(membro, campo) != novo
        }
        self.membros.apply(membro, efeitos)
        self.audit.registrar(
            ator.igreja_id, ator.id, "evento_eclesiastico_registrado", "membro", membro.id,
            {"tipo": data.tipo.value, "evento_id": str(evento.id), "alteracoes": alteracoes},
            commit=False,
        )
        self._commit()
        self.db.refresh(evento)
        self.db.refresh(membro)
        return evento, membro

    # ---------- internos ----------

    def _validar_familia(self, ator: Usuario, familia_id: uuid.UUID | None) -> None:
        if familia_id is not None and (
            self.familias.get_in_church(ator.igreja_id, familia_id) is None
        ):
            raise NotFoundError("Família não encontrada")

    def _commit(self) -> None:
        try:
            self.db.commit()
        except IntegrityError:
            # Corrida entre dois cadastros com o mesmo número do rol
            self.db.rollback()
            raise ConflictError("Número do rol já em uso")


def _seguro_csv(valor):
    """Evita injeção de fórmula ao abrir o CSV no Excel/Calc."""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valor
    return "" if valor is None else valor
