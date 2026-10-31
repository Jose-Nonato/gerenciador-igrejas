// Espelha os schemas do backend (back/schemas e back/models/enums.py)

export type Perfil = 'admin' | 'pastor' | 'presbitero' | 'usuario'
export type StatusUsuario = 'ativo' | 'bloqueado' | 'convite_pendente' | 'desativado'
export type Rol = 'C' | 'NC'
export type Sexo = 'masculino' | 'feminino'
export type EstadoCivil = 'solteiro' | 'casado' | 'viuvo' | 'divorciado'
export type SituacaoMembro = 'ativo' | 'em_disciplina' | 'transferido' | 'falecido' | 'excluido'
export type Oficio = 'nenhum' | 'presbitero' | 'diacono'

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  troca_obrigatoria: boolean
}

export interface Usuario {
  id: string
  igreja_id: string
  membro_id: string | null
  email: string
  perfil: Perfil
  status: StatusUsuario
  troca_obrigatoria: boolean
  ultimo_acesso: string | null
}

export interface Membro {
  id: string
  familia_id: string | null
  numero_rol: number | null
  rol: Rol
  nome: string
  data_nascimento: string | null
  sexo: Sexo | null
  estado_civil: EstadoCivil | null
  telefone: string | null
  email: string | null
  endereco: string | null
  situacao: SituacaoMembro
  oficio: Oficio
  criado_em: string
  atualizado_em: string
}

export interface MembroPage {
  items: Membro[]
  total: number
  limit: number
  offset: number
}

export interface FiltroMembros {
  q?: string
  rol?: Rol
  situacao?: SituacaoMembro
  oficio?: Oficio
  limit?: number
  offset?: number
}
