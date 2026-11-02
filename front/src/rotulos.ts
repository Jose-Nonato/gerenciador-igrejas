import type {
  CargoLideranca,
  CategoriaPost,
  EstadoCivil,
  FormaRecepcao,
  Oficio,
  Perfil,
  Rol,
  Sexo,
  SiglaSociedade,
  SituacaoMembro,
  StatusPost,
  StatusPresenca,
  StatusUsuario,
  TipoEvento,
  TipoPublico,
  TipoSocio,
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

export const SIGLA: Record<SiglaSociedade, string> = {
  UCP: 'União de Crianças Presbiterianas',
  UPA: 'União Presbiteriana de Adolescentes',
  UMP: 'União de Mocidade Presbiteriana',
  SAF: 'Sociedade Auxiliadora Feminina',
  UPH: 'União Presbiteriana de Homens',
}

export const SIGLAS = Object.keys(SIGLA) as SiglaSociedade[]

export const TIPO_SOCIO: Record<TipoSocio, string> = {
  ativo: 'Sócio ativo',
  cooperador: 'Cooperador',
  nao_membro: 'Não membro',
}

export const STATUS_PRESENCA: Record<StatusPresenca, string> = {
  P: 'Presente',
  A: 'Ausente',
  J: 'Justificado',
}

export const CARGO: Record<CargoLideranca, string> = {
  presidente: 'Presidente',
  vice_presidente: 'Vice-presidente',
  secretario: 'Secretário(a)',
  tesoureiro: 'Tesoureiro(a)',
  conselheiro: 'Conselheiro(a)',
  outro: 'Outro cargo',
}

export const CATEGORIA: Record<CategoriaPost, string> = {
  aviso: 'Aviso',
  evento: 'Evento',
  pastoral: 'Mensagem pastoral',
  oracao: 'Pedido de oração',
}

export const STATUS_POST: Record<StatusPost, string> = {
  rascunho: 'Rascunho',
  agendado: 'Agendado',
  publicado: 'Publicado',
}

export const PUBLICO: Record<TipoPublico, string> = {
  igreja: 'Toda a igreja',
  comungantes: 'Comungantes',
  oficiais: 'Oficiais (presbíteros e diáconos)',
  sociedade: 'Uma sociedade',
  professores_ebd: 'Professores da EBD',
}

export function rotuloPublico(c: { publico: TipoPublico; sociedade_sigla: string | null }): string {
  return c.publico === 'sociedade' ? `Sociedade ${c.sociedade_sigla ?? ''}`.trim() : PUBLICO[c.publico]
}
