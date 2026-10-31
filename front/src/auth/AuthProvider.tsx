import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getTokens, setSessionExpiredHandler, setTokens } from '../api/client'
import { authApi } from '../api/endpoints'
import type { Usuario } from '../api/types'
import { AuthContext, type AuthState } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [carregando, setCarregando] = useState(() => getTokens() !== null)
  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => {
    setSessionExpiredHandler(() => setUsuario(null))
    if (!getTokens()) return
    let ativo = true
    authApi
      .eu()
      .then((u) => ativo && setUsuario(u))
      .catch(() => ativo && setUsuario(null))
      .finally(() => ativo && setCarregando(false))
    return () => {
      ativo = false
    }
  }, [])

  const login = useCallback(async (email: string, senha: string) => {
    const tokens = await authApi.login(email, senha)
    setTokens({ access_token: tokens.access_token, refresh_token: tokens.refresh_token })
    const eu = await authApi.eu()
    setAviso(null)
    setUsuario(eu)
    return eu
  }, [])

  const descartarSessao = useCallback((mensagem?: string) => {
    setTokens(null)
    setAviso(mensagem ?? null)
    setUsuario(null)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // sem rede ou token já inválido: encerra a sessão local de qualquer forma
    }
    descartarSessao()
  }, [descartarSessao])

  const valor = useMemo<AuthState>(
    () => ({ usuario, carregando, aviso, login, logout, descartarSessao }),
    [usuario, carregando, aviso, login, logout, descartarSessao],
  )
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}
