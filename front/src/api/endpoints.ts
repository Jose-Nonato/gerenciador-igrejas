import { api, apiBlob } from './client'
import type {
  AtualizacaoMembro,
  AtualizacaoSocio,
  AtualizacaoUsuario,
  Evento,
  Familia,
  FiltroMembros,
  Frequencia,
  ItemPresenca,
  Membro,
  MembroPage,
  NovaReuniao,
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
  convidar: (email: string, perfil: Perfil) =>
    api<Usuario>('/usuarios', { method: 'POST', json: { email, perfil } }),
  atualizar: (id: string, dados: AtualizacaoUsuario) =>
    api<Usuario>(`/usuarios/${id}`, { method: 'PATCH', json: dados }),
  reenviarConvite: (id: string) => api<void>(`/usuarios/${id}/convite`, { method: 'POST' }),
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

  socios: (id: string, incluirEx = false) =>
    api<Socio[]>(`/sociedades/${id}/socios`, { query: { incluir_ex: incluirEx ? 'true' : undefined } }),
  adicionarSocio: (id: string, dados: NovoSocio) =>
    api<Socio>(`/sociedades/${id}/socios`, { method: 'POST', json: dados }),
  atualizarSocio: (id: string, socioId: string, dados: AtualizacaoSocio) =>
    api<Socio>(`/sociedades/${id}/socios/${socioId}`, { method: 'PATCH', json: dados }),
  /** O sócio sai da sociedade (data de saída); a presença histórica é mantida */
  removerSocio: (id: string, socioId: string) =>
    api<void>(`/sociedades/${id}/socios/${socioId}`, { method: 'DELETE' }),

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
