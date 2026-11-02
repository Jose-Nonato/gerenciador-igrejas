"""Enums da modelagem (aba Enums/Campos da planilha).

No banco são VARCHAR + CHECK (não enum nativo do Postgres), o que evita
`ALTER TYPE` nas migrações quando um valor novo for acrescentado.

Sexo, EstadoCivil e FormaRecepcao NÃO constam da aba Enums da planilha: os valores
abaixo são uma proposta, a confirmar. Alterá-los exige uma migração (CHECK no banco).
"""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def enum_column(enum_cls: type[StrEnum]) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=enum_cls.__name__.lower(),
        native_enum=False,
        create_constraint=True,
        length=max(len(m.value) for m in enum_cls),
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class Rol(StrEnum):
    COMUNGANTE = "C"
    NAO_COMUNGANTE = "NC"


class Sexo(StrEnum):
    MASCULINO = "masculino"
    FEMININO = "feminino"


class EstadoCivil(StrEnum):
    SOLTEIRO = "solteiro"
    CASADO = "casado"
    VIUVO = "viuvo"
    DIVORCIADO = "divorciado"


class FormaRecepcao(StrEnum):
    TRANSFERENCIA = "transferencia"
    JURISDICAO = "jurisdicao"
    PROFISSAO_FE = "profissao_fe"
    BATISMO_PROFISSAO_FE = "batismo_profissao_fe"


class SituacaoMembro(StrEnum):
    ATIVO = "ativo"
    EM_DISCIPLINA = "em_disciplina"
    TRANSFERIDO = "transferido"
    FALECIDO = "falecido"
    EXCLUIDO = "excluido"


class Oficio(StrEnum):
    NENHUM = "nenhum"
    PRESBITERO = "presbitero"
    DIACONO = "diacono"


class TipoEventoEclesiastico(StrEnum):
    BATISMO = "batismo"
    PROFISSAO_FE = "profissao_fe"
    RECEPCAO = "recepcao"
    ORDENACAO = "ordenacao"
    DISCIPLINA = "disciplina"
    RESTAURACAO = "restauracao"
    SAIDA = "saida"


class PerfilUsuario(StrEnum):
    ADMIN = "admin"
    PASTOR = "pastor"
    PRESBITERO = "presbitero"
    USUARIO = "usuario"


class StatusUsuario(StrEnum):
    ATIVO = "ativo"
    BLOQUEADO = "bloqueado"
    CONVITE_PENDENTE = "convite_pendente"
    DESATIVADO = "desativado"


class SiglaSociedade(StrEnum):
    UCP = "UCP"
    UPA = "UPA"
    UMP = "UMP"
    SAF = "SAF"
    UPH = "UPH"


class TipoSocio(StrEnum):
    ATIVO = "ativo"
    COOPERADOR = "cooperador"
    NAO_MEMBRO = "nao_membro"


class CargoLideranca(StrEnum):
    """Cargos da diretoria de uma sociedade. Os quatro primeiros têm um único ocupante
    por vez; conselheiro e outro admitem vários."""

    PRESIDENTE = "presidente"
    VICE_PRESIDENTE = "vice_presidente"
    SECRETARIO = "secretario"
    TESOUREIRO = "tesoureiro"
    CONSELHEIRO = "conselheiro"
    OUTRO = "outro"


# Cargos com um único ocupante em exercício por sociedade
CARGOS_UNICOS = frozenset(
    {
        CargoLideranca.PRESIDENTE,
        CargoLideranca.VICE_PRESIDENTE,
        CargoLideranca.SECRETARIO,
        CargoLideranca.TESOUREIRO,
    }
)


class StatusPresenca(StrEnum):
    PRESENTE = "P"
    AUSENTE = "A"
    JUSTIFICADO = "J"


class CategoriaPost(StrEnum):
    AVISO = "aviso"
    EVENTO = "evento"
    PASTORAL = "pastoral"
    ORACAO = "oracao"


class StatusPost(StrEnum):
    RASCUNHO = "rascunho"
    AGENDADO = "agendado"
    PUBLICADO = "publicado"


class TipoPublico(StrEnum):
    IGREJA = "igreja"
    COMUNGANTES = "comungantes"
    OFICIAIS = "oficiais"
    SOCIEDADE = "sociedade"
    PROFESSORES_EBD = "professores_ebd"


class FormatoAtendimento(StrEnum):
    IGREJA = "igreja"
    CASA = "casa"
    VIDEO = "video"
    TELEFONE = "telefone"


class StatusAgendamento(StrEnum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    SUGERIDO = "sugerido"
    RECUSADO = "recusado"
    CANCELADO = "cancelado"
