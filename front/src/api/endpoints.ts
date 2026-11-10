import { api, apiBlob } from './client'
import type {
  AtualizacaoMembro,
  AtualizacaoSocio,
  AtualizacaoComunicado,
  AtualizacaoUsuario,
  Comunicado,
  ComunicadoPage,
  ConviteEmMassa,
  ConviteLink,
  Evento,
  Familia,
  FiltroComunicados,
  FiltroMembros,
  Frequencia,
  ItemPresenca,
  Lideranca,
  Membro,
  MembroPage,
  MembroResumo,
  NovaReuniao,
  NovaLideranca,
  NovoComunicado,
  NovoEvento,
  NovoMembro,
  NovoSocio,
  Perfil,
  RegistroEvento,
  Reuniao,
  ReuniaoDetalhe,
  SiglaSociedade,
  Sociedade,
  Socio,
  TokenPair,
  Usuario,
} from './types'

export const authApi = {
  login: (email: string, senha: string) =>
    api<TokenPair>('/auth/login', { method: 'POST', form: { username: email, password: senha }, auth: false }),
  logout: () => api<void>('/auth/logout', { method: 'POST' }),
  trocarSenha: (senhaAtual: string, novaSenha: string) =>
    api<void>('/auth/change-password', {
      method: 'POST',
      json: { current_password: senhaAtual, new_password: novaSenha },
    }),
  esqueciSenha: (email: string) =>
    api<void>('/auth/esqueci-senha', { method: 'POST', json: { email }, auth: false }),
  redefinirSenha: (token: string, novaSenha: string) =>
    api<void>('/auth/redefinir-senha', { method: 'POST', json: { token, nova_senha: novaSenha }, auth: false }),
  eu: () => api<Usuario>('/usuarios/me'),
}

export const usuariosApi = {
  listar: () => api<Usuario[]>('/usuarios'),
  /** Com `membroId`, a conta já nasce ligada ao membro */
  convidar: (email: string, perfil: Perfil, membroId?: string) =>
    api<Usuario>('/usuarios', { method: 'POST', json: { email, perfil, membro_id: membroId ?? null } }),
  /** Convida os membros do rol com e-mail e sem conta. `simular` só conta. */
  convidarEmMassa: (simular: boolean, limite = 50) =>
    api<ConviteEmMassa>('/usuarios/convites-em-massa', { method: 'POST', json: { simular, limite } }),
  atualizar: (id: string, dados: AtualizacaoUsuario) =>
    api<Usuario>(`/usuarios/${id}`, { method: 'PATCH', json: dados }),
  reenviarConvite: (id: string) => api<void>(`/usuarios/${id}/convite`, { method: 'POST' }),
  /** Gera um novo link de convite para copiar (sem e-mail); o anterior deixa de valer */
  linkConvite: (id: string) => api<ConviteLink>(`/usuarios/${id}/link-convite`, { method: 'POST' }),
}

export const membrosApi = {
  listar: (filtro: FiltroMembros) => api<MembroPage>('/membros', { query: { ...filtro } }),
  obter: (id: string) => api<Membro>(`/membros/${id}`),
  criar: (dados: NovoMembro) => api<Membro>('/membros', { method: 'POST', json: dados }),
  atualizar: (id: string, dados: AtualizacaoMembro) =>
    api<Membro>(`/membros/${id}`, { method: 'PATCH', json: dados }),
  /** Exclusão lógica: o backend mantém a linha e a auditoria */
  excluir: (id: string) => api<void>(`/membros/${id}`, { method: 'DELETE' }),
  eventos: (id: string) => api<Evento[]>(`/membros/${id}/eventos`),
  registrarEvento: (id: string, dados: NovoEvento) =>
    api<RegistroEvento>(`/membros/${id}/eventos`, { method: 'POST', json: dados }),
  exportarCsv: (filtro: FiltroMembros) => apiBlob('/membros/exportar', { query: { ...filtro } }),
}

export const familiasApi = {
  listar: () => api<Familia[]>('/familias'),
  criar: (nome: string) => api<Familia>('/familias', { method: 'POST', json: { nome } }),
}

export const sociedadesApi = {
  listar: () => api<Sociedade[]>('/sociedades'),
  obter: (id: string) => api<Sociedade>(`/sociedades/${id}`),
  criar: (sigla: SiglaSociedade, nome: string | null) =>
    api<Sociedade>('/sociedades', { method: 'POST', json: { sigla, nome } }),
  atualizar: (id: string, nome: string | null) =>
    api<Sociedade>(`/sociedades/${id}`, { method: 'PATCH', json: { nome } }),

  /** Busca mínima (nome e nº do rol) para cadastrar sócios; vale também para quem não vê o rol */
  buscarMembros: (id: string, q: string) =>
    api<MembroResumo[]>(`/sociedades/${id}/membros`, { query: { q } }),
  socios: (id: string, incluirEx = false) =>
    api<Socio[]>(`/sociedades/${id}/socios`, { query: { incluir_ex: incluirEx ? 'true' : undefined } }),
  adicionarSocio: (id: string, dados: NovoSocio) =>
    api<Socio>(`/sociedades/${id}/socios`, { method: 'POST', json: dados }),
  atualizarSocio: (id: string, socioId: string, dados: AtualizacaoSocio) =>
    api<Socio>(`/sociedades/${id}/socios/${socioId}`, { method: 'PATCH', json: dados }),
  /** O sócio sai da sociedade (data de saída); a presença histórica é mantida */
  removerSocio: (id: string, socioId: string) =>
    api<void>(`/sociedades/${id}/socios/${socioId}`, { method: 'DELETE' }),

  lideranca: (id: string, incluirEncerrados = false) =>
    api<Lideranca[]>(`/sociedades/${id}/lideranca`, {
      query: { incluir_encerrados: incluirEncerrados ? 'true' : undefined },
    }),
  adicionarLideranca: (id: string, dados: NovaLideranca) =>
    api<Lideranca>(`/sociedades/${id}/lideranca`, { method: 'POST', json: dados }),
  /** Encerra o mandato na data informada; o registro e o histórico permanecem */
  encerrarLideranca: (id: string, liderancaId: string, fim: string) =>
    api<Lideranca>(`/sociedades/${id}/lideranca/${liderancaId}`, { method: 'PATCH', json: { fim } }),

  reunioes: (id: string) => api<Reuniao[]>(`/sociedades/${id}/reunioes`),
  reuniao: (id: string, reuniaoId: string) =>
    api<ReuniaoDetalhe>(`/sociedades/${id}/reunioes/${reuniaoId}`),
  criarReuniao: (id: string, dados: NovaReuniao) =>
    api<ReuniaoDetalhe>(`/sociedades/${id}/reunioes`, { method: 'POST', json: dados }),
  atualizarReuniao: (id: string, reuniaoId: string, dados: { data?: string; tema?: string | null }) =>
    api<ReuniaoDetalhe>(`/sociedades/${id}/reunioes/${reuniaoId}`, { method: 'PATCH', json: dados }),
  lancarPresencas: (id: string, reuniaoId: string, presencas: ItemPresenca[]) =>
    api<ReuniaoDetalhe>(`/sociedades/${id}/reunioes/${reuniaoId}/presencas`, {
      method: 'PUT',
      json: { presencas },
    }),

  frequencia: (id: string, de?: string, ate?: string) =>
    api<Frequencia>(`/sociedades/${id}/frequencia`, { query: { de, ate } }),
}

export const comunicadosApi = {
  /** O que foi publicado para o público do usuário */
  mural: (filtro: FiltroComunicados) => api<ComunicadoPage>('/comunicados', { query: { ...filtro } }),
  /** Para quem escreve: inclui rascunhos e agendados */
  gerenciar: (filtro: FiltroComunicados) =>
    api<ComunicadoPage>('/comunicados/gerenciar', { query: { ...filtro } }),
  obter: (id: string) => api<Comunicado>(`/comunicados/${id}`),
  criar: (dados: NovoComunicado) => api<Comunicado>('/comunicados', { method: 'POST', json: dados }),
  atualizar: (id: string, dados: AtualizacaoComunicado) =>
    api<Comunicado>(`/comunicados/${id}`, { method: 'PATCH', json: dados }),
  /** Sem `quando` (ou no passado): publica agora. No futuro: agenda. */
  publicar: (id: string, quando?: string) =>
    api<Comunicado>(`/comunicados/${id}/publicar`, { method: 'POST', json: { quando: quando ?? null } }),
  despublicar: (id: string) => api<Comunicado>(`/comunicados/${id}/despublicar`, { method: 'POST' }),
  /** Exclusão lógica */
  excluir: (id: string) => api<void>(`/comunicados/${id}`, { method: 'DELETE' }),
  /** Define ou troca a imagem (JPEG, PNG, GIF ou WebP, até 5 MB) */
  enviarImagem: (id: string, arquivo: File) => {
    const dados = new FormData()
    dados.append('arquivo', arquivo)
    return api<Comunicado>(`/comunicados/${id}/imagem`, { method: 'PUT', arquivo: dados })
  },
  removerImagem: (id: string) => api<Comunicado>(`/comunicados/${id}/imagem`, { method: 'DELETE' }),
  /** A rota exige login, então a imagem vem como blob (um <img src> não envia o token) */
  imagem: (id: string) => apiBlob(`/comunicados/${id}/imagem`),
}
