import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { PERFIL } from '../rotulos'

export function Layout() {
  const { usuario, logout } = useAuth()
  const navegar = useNavigate()
  const equipe = usuario?.perfil !== 'usuario'

  async function sair() {
    await logout()
    navegar('/login', { replace: true })
  }

  // Troca de senha obrigatória: sem menu, só a tela de troca
  if (usuario?.troca_obrigatoria) return <Outlet />

  return (
    <div className="app">
      <header className="topo">
        <span className="marca">Gerenciador de Igrejas</span>
        <nav aria-label="Principal">
          <NavLink to="/" end>
            Início
          </NavLink>
          {equipe && <NavLink to="/membros">Rol de membros</NavLink>}
          <NavLink to="/trocar-senha">Alterar senha</NavLink>
        </nav>
        <div className="usuario">
          <span title={usuario?.email}>
            {usuario?.email} · {usuario ? PERFIL[usuario.perfil] : ''}
          </span>
          <button type="button" className="botao secundario" onClick={sair}>
            Sair
          </button>
        </div>
      </header>
      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  )
}
