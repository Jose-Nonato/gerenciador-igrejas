import type {
  EstadoCivil,
  FormaRecepcao,
  Oficio,
  Perfil,
  Rol,
  Sexo,
  SituacaoMembro,
  StatusUsuario,
  TipoEvento,
} from './api/types'

export const PERFIL: Record<Perfil, string> = {
  admin: 'Administrador',
  pastor: 'Pastor',
  presbitero: 'Presbítero',
  usuario: 'Usuário',
}

export const ROL: Record<Rol, string> = {
  C: 'Comungante',
  NC: 'Não comungante',
}

export const SITUACAO: Record<SituacaoMembro, string> = {
  ativo: 'Ativo',
  em_disciplina: 'Em disciplina',
  transferido: 'Transferido',
  falecido: 'Falecido',
  excluido: 'Excluído',
}

export const OFICIO: Record<Oficio, string> = {
  nenhum: '—',
  presbitero: 'Presbítero',
  diacono: 'Diácono',
}

export const SEXO: Record<Sexo, string> = {
  masculino: 'Masculino',
  feminino: 'Feminino',
}

export const ESTADO_CIVIL: Record<EstadoCivil, string> = {
  solteiro: 'Solteiro(a)',
  casado: 'Casado(a)',
  viuvo: 'Viúvo(a)',
  divorciado: 'Divorciado(a)',
}

export const TIPO_EVENTO: Record<TipoEvento, string> = {
  batismo: 'Batismo',
  profissao_fe: 'Profissão de fé',
  recepcao: 'Recepção',
  ordenacao: 'Ordenação',
  disciplina: 'Disciplina',
  restauracao: 'Restauração',
  saida: 'Saída',
}

export const FORMA_RECEPCAO: Record<FormaRecepcao, string> = {
  transferencia: 'Transferência',
  jurisdicao: 'Jurisdição',
  profissao_fe: 'Profissão de fé',
  batismo_profissao_fe: 'Batismo e profissão de fé',
}

export const STATUS_USUARIO: Record<StatusUsuario, string> = {
  ativo: 'Ativo',
  bloqueado: 'Bloqueado',
  convite_pendente: 'Convite pendente',
  desativado: 'Desativado',
}
