import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Perfil } from '../api/types'
import { Carregando } from '../components/Carregando'
import { useAuth } from './useAuth'

interface Props {
  /** Perfis aceitos; sem a lista, qualquer usuário autenticado entra */
  perfis?: Perfil[]
}

export function RequireAuth({ perfis }: Props) {
  const { usuario, carregando } = useAuth()
  const local = useLocation()

  if (carregando) return <Carregando />
  if (!usuario) return <Navigate to="/login" replace state={{ de: local.pathname }} />

  // Enquanto a troca de senha é obrigatória, o backend recusa todo o resto (403)
  if (usuario.troca_obrigatoria && local.pathname !== '/trocar-senha') {
    return <Navigate to="/trocar-senha" replace />
  }
  if (perfis && !perfis.includes(usuario.perfil)) return <Navigate to="/" replace />

  return <Outlet />
}
