import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { PERFIL } from '../rotulos'

export function InicioPage() {
  const { usuario } = useAuth()
  if (!usuario) return null
  const equipe = usuario.perfil !== 'usuario'

  return (
    <section className="pagina">
      <h1>Bem-vindo</h1>
      <p className="subtitulo">
        Você está conectado como <strong>{usuario.email}</strong> ({PERFIL[usuario.perfil]}).
      </p>
      {equipe ? (
        <div className="atalhos">
          <Link to="/membros" className="atalho">
            <strong>Rol de membros</strong>
            <span>Consulte e exporte os membros da igreja.</span>
          </Link>
        </div>
      ) : (
        <p>Novas funcionalidades para membros estarão disponíveis em breve.</p>
      )}
    </section>
  )
}
