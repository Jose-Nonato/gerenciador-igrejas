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
  /** Conta de acesso ligada ao membro; null = sem acesso ao sistema */
  acesso: AcessoMembro | null
}

export interface AcessoMembro {
  id: string
  email: string
  perfil: Perfil
  status: StatusUsuario
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

export interface Familia {
  id: string
  nome: string
  endereco: string | null
}

/** Corpo de POST /membros; campos opcionais vazios devem ser omitidos ou null. */
export interface NovoMembro {
  nome: string
  rol: Rol
  familia_id?: string | null
  numero_rol?: number | null
  data_nascimento?: string | null
  sexo?: Sexo | null
  estado_civil?: EstadoCivil | null
  telefone?: string | null
  email?: string | null
  endereco?: string | null
  situacao?: SituacaoMembro
  oficio?: Oficio
}

/** Corpo de PATCH /membros/{id}: rol, situação e ofício só mudam por eventos eclesiásticos. */
export type AtualizacaoMembro = Omit<NovoMembro, 'rol' | 'situacao' | 'oficio'>

export type TipoEvento =
  | 'batismo'
  | 'profissao_fe'
  | 'recepcao'
  | 'ordenacao'
  | 'disciplina'
  | 'restauracao'
  | 'saida'
export type FormaRecepcao = 'transferencia' | 'jurisdicao' | 'profissao_fe' | 'batismo_profissao_fe'

export interface Evento {
  id: string
  membro_id: string
  tipo: TipoEvento
  forma_recepcao: FormaRecepcao | null
  data: string
  ata_conselho: string | null
  igreja_relacionada: string | null
  observacao: string | null
  oficio: Oficio | null
  situacao_resultante: SituacaoMembro | null
}

/** Corpo de POST /membros/{id}/eventos; campos que não se aplicam ao tipo ficam de fora. */
export interface NovoEvento {
  tipo: TipoEvento
  data: string
  ata_conselho?: string | null
  forma_recepcao?: FormaRecepcao | null
  igreja_relacionada?: string | null
  observacao?: string | null
  oficio?: Oficio | null
  situacao_resultante?: SituacaoMembro | null
}

export interface RegistroEvento {
  evento: Evento
  membro: Membro
}

/** Corpo de PATCH /usuarios/{id}; `membro_id: null` desvincula, omitir não mexe. */
export interface AtualizacaoUsuario {
  email?: string
  perfil?: Perfil
  status?: StatusUsuario
  membro_id?: string | null
}

// ---------- sociedades ----------

export type SiglaSociedade = 'UCP' | 'UPA' | 'UMP' | 'SAF' | 'UPH'
export type TipoSocio = 'ativo' | 'cooperador' | 'nao_membro'
export type StatusPresenca = 'P' | 'A' | 'J'

export interface Sociedade {
  id: string
  sigla: SiglaSociedade
  nome: string | null
  total_socios: number
}

export interface Socio {
  id: string
  sociedade_id: string
  membro_id: string | null
  nome: string
  tipo: TipoSocio
  entrou_em: string
  saiu_em: string | null
}

/** Corpo de POST /sociedades/{id}/socios: membro_id para ativo/cooperador, nome_externo para nao_membro. */
export interface NovoSocio {
  tipo: TipoSocio
  membro_id?: string | null
  nome_externo?: string | null
}

export interface AtualizacaoSocio {
  tipo?: TipoSocio
  nome_externo?: string
}

export interface Reuniao {
  id: string
  sociedade_id: string
  data: string
  tema: string | null
  presentes: number
  ausentes: number
  justificados: number
}

export interface ItemPresenca {
  socio_id: string
  status: StatusPresenca
}

export interface PresencaDetalhe extends ItemPresenca {
  nome: string
}

export interface ReuniaoDetalhe extends Reuniao {
  presencas: PresencaDetalhe[]
}

export interface NovaReuniao {
  data: string
  tema?: string | null
  presencas?: ItemPresenca[]
}

export interface FrequenciaSocio {
  socio_id: string
  nome: string
  tipo: TipoSocio
  presentes: number
  ausentes: number
  justificados: number
  sem_registro: number
  percentual_presenca: number | null
}

export interface Frequencia {
  de: string | null
  ate: string | null
  total_reunioes: number
  socios: FrequenciaSocio[]
}

export type CargoLideranca =
  | 'presidente'
  | 'vice_presidente'
  | 'secretario'
  | 'tesoureiro'
  | 'conselheiro'
  | 'outro'

export interface Lideranca {
  id: string
  sociedade_id: string
  membro_id: string
  nome: string
  cargo: CargoLideranca
  cargo_descricao: string | null
  inicio: string
  /** Nulo = em exercício */
  fim: string | null
}

export interface NovaLideranca {
  membro_id: string
  cargo: CargoLideranca
  cargo_descricao?: string | null
  inicio?: string
}

/** Dados mínimos de um membro (a busca restrita das sociedades não revela o resto). */
export interface MembroResumo {
  id: string
  nome: string
  numero_rol: number | null
}

// ---------- comunicados ----------

export type CategoriaPost = 'aviso' | 'evento' | 'pastoral' | 'oracao'
export type StatusPost = 'rascunho' | 'agendado' | 'publicado'
export type TipoPublico = 'igreja' | 'comungantes' | 'oficiais' | 'sociedade' | 'professores_ebd'

export interface Comunicado {
  id: string
  titulo: string
  corpo: string
  categoria: CategoriaPost
  publico: TipoPublico
  sociedade_id: string | null
  sociedade_sigla: string | null
  /** Efetivo: um agendado cuja hora já chegou vem como publicado */
  status: StatusPost
  publicar_em: string | null
  data_publicacao: string | null
  autor: string | null
  criado_em: string
  atualizado_em: string
}

export interface ComunicadoPage {
  items: Comunicado[]
  total: number
  limit: number
  offset: number
}

export interface NovoComunicado {
  titulo: string
  corpo: string
  categoria: CategoriaPost
  publico: TipoPublico
  sociedade_id?: string | null
}

export type AtualizacaoComunicado = Partial<NovoComunicado>

export interface FiltroComunicados {
  categoria?: CategoriaPost
  status?: StatusPost
  limit?: number
  offset?: number
}

export interface ConviteEmMassa {
  simulacao: boolean
  /** Membros no rol, sem conta e com e-mail livre */
  elegiveis: number
  convidados: number
  /** Elegíveis ainda sem convite (chame de novo) */
  restantes: number
  sem_email: number
  email_em_uso: number
}
