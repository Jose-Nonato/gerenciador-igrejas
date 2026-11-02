import type { EstadoCivil, Oficio, Perfil, Rol, Sexo, SituacaoMembro } from './api/types'

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
