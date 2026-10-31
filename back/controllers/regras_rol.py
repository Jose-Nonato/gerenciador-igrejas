"""Regras de negócio do rol: o que cada evento eclesiástico faz com o membro.

Função pura (sem banco) para ser fácil de testar e de ajustar às normas da igreja.
"""

from core.exceptions import AppError, ConflictError
from models import Membro
from models.enums import (
    FormaRecepcao,
    Oficio,
    Rol,
    SituacaoMembro,
    TipoEventoEclesiastico as Tipo,
)
from schemas import EventoCreate

# Só o batismo pode ser registrado sem ata do Conselho
_SEM_ATA = {Tipo.BATISMO}
_OFICIOS_ORDENAVEIS = {Oficio.PRESBITERO, Oficio.DIACONO}
_MOTIVOS_SAIDA = {SituacaoMembro.TRANSFERIDO, SituacaoMembro.FALECIDO, SituacaoMembro.EXCLUIDO}


def calcular_efeitos(membro: Membro, ev: EventoCreate) -> dict:
    """Valida o evento contra o estado atual e devolve os campos do membro a alterar."""
    if membro.situacao == SituacaoMembro.FALECIDO:
        raise ConflictError("Membro falecido não admite novos eventos")
    if membro.situacao in (SituacaoMembro.TRANSFERIDO, SituacaoMembro.EXCLUIDO) and (
        ev.tipo != Tipo.RECEPCAO
    ):
        raise ConflictError("Membro fora do rol só pode ser recebido novamente")

    if ev.tipo not in _SEM_ATA and not (ev.ata_conselho and ev.ata_conselho.strip()):
        raise AppError("Informe a ata do Conselho")
    if ev.forma_recepcao is not None and ev.tipo != Tipo.RECEPCAO:
        raise AppError("forma_recepcao só se aplica à recepção")
    if ev.oficio is not None and ev.tipo != Tipo.ORDENACAO:
        raise AppError("oficio só se aplica à ordenação")
    if ev.situacao_resultante is not None and ev.tipo != Tipo.SAIDA:
        raise AppError("situacao_resultante só se aplica à saída")

    if ev.tipo == Tipo.BATISMO:
        return {}

    if ev.tipo == Tipo.PROFISSAO_FE:
        return {"rol": Rol.COMUNGANTE}

    if ev.tipo == Tipo.RECEPCAO:
        if ev.forma_recepcao is None:
            raise AppError("Informe a forma de recepção")
        return {"rol": Rol.COMUNGANTE, "situacao": SituacaoMembro.ATIVO}

    if ev.tipo == Tipo.ORDENACAO:
        if ev.oficio not in _OFICIOS_ORDENAVEIS:
            raise AppError("Informe o ofício: presbitero ou diacono")
        if membro.situacao != SituacaoMembro.ATIVO:
            raise ConflictError("Só membros ativos podem ser ordenados")
        if membro.rol != Rol.COMUNGANTE:
            raise ConflictError("Só comungantes podem ser ordenados")
        return {"oficio": ev.oficio}

    if ev.tipo == Tipo.DISCIPLINA:
        if membro.situacao != SituacaoMembro.ATIVO:
            raise ConflictError("Só membros ativos podem ser colocados em disciplina")
        return {"situacao": SituacaoMembro.EM_DISCIPLINA}

    if ev.tipo == Tipo.RESTAURACAO:
        if membro.situacao != SituacaoMembro.EM_DISCIPLINA:
            raise ConflictError("Só membros em disciplina podem ser restaurados")
        return {"situacao": SituacaoMembro.ATIVO}

    if ev.tipo == Tipo.SAIDA:
        if ev.situacao_resultante not in _MOTIVOS_SAIDA:
            raise AppError("Informe situacao_resultante: transferido, falecido ou excluido")
        return {"situacao": ev.situacao_resultante}

    raise AppError("Tipo de evento não suportado")  # pragma: no cover
