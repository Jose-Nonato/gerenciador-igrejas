import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { PERFIL } from '../rotulos'
import { useAcessoSociedades } from '../useAcessoSociedades'

export function InicioPage() {
  const { usuario } = useAuth()
  const sociedades = useAcessoSociedades()
  if (!usuario) return null
  const equipe = usuario.perfil !== 'usuario'

  return (
    <section className="pagina">
      <h1>Bem-vindo</h1>
      <p className="subtitulo">
        Você está conectado como <strong>{usuario.email}</strong> ({PERFIL[usuario.perfil]}).
      </p>
      <div className="atalhos">
        <Link to="/comunicados" className="atalho">
          <strong>Comunicados</strong>
          <span>Avisos, eventos e mensagens da igreja.</span>
        </Link>
        {equipe && (
          <Link to="/membros" className="atalho">
            <strong>Rol de membros</strong>
            <span>Consulte e exporte os membros da igreja.</span>
          </Link>
        )}
        {sociedades.temAcesso && (
          <Link to="/sociedades" className="atalho">
            <strong>{sociedades.gestor ? 'Sociedades internas' : 'Minha sociedade'}</strong>
            <span>Sócios, reuniões, presença e frequência.</span>
          </Link>
        )}
      </div>
    </section>
  )
}
