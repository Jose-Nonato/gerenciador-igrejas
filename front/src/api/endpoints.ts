import { api, apiBlob } from './client'
import type { FiltroMembros, Membro, MembroPage, TokenPair, Usuario } from './types'

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

export const membrosApi = {
  listar: (filtro: FiltroMembros) => api<MembroPage>('/membros', { query: { ...filtro } }),
  obter: (id: string) => api<Membro>(`/membros/${id}`),
  exportarCsv: (filtro: FiltroMembros) => apiBlob('/membros/exportar', { query: { ...filtro } }),
}
