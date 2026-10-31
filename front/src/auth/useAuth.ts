import { createContext, useContext } from 'react'
import type { Usuario } from '../api/types'

export interface AuthState {
  usuario: Usuario | null
  /** true enquanto a sessão guardada está sendo validada na abertura do app */
  carregando: boolean
  login: (email: string, senha: string) => Promise<Usuario>
  logout: () => Promise<void>
  /** Mensagem para a tela de login depois de a sessão ser encerrada de propósito */
  aviso: string | null
  /** Esquece a sessão só no navegador, sem chamar a API (ex.: o backend já a encerrou) */
  descartarSessao: (aviso?: string) => void
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de <AuthProvider>')
  return ctx
}
