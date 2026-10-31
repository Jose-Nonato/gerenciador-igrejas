import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { CartaoAuth } from '../components/CartaoAuth'
import { Campo } from '../components/Campo'

interface EstadoRota {
  de?: string
  aviso?: string
}

export function LoginPage() {
  const { usuario, login, aviso: avisoSessao } = useAuth()
  const navegar = useNavigate()
  const estado = (useLocation().state ?? {}) as EstadoRota
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (usuario && !enviando) {
    return <Navigate to={usuario.troca_obrigatoria ? '/trocar-senha' : '/'} replace />
  }

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      const eu = await login(email.trim(), senha)
      // Voltar à tela de troca de senha logo após entrar não faz sentido: vai para o início
      const destino = estado.de && estado.de !== '/trocar-senha' ? estado.de : '/'
      navegar(eu.troca_obrigatoria ? '/trocar-senha' : destino, { replace: true })
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível entrar.')
      setEnviando(false)
    }
  }

  return (
    <CartaoAuth titulo="Entrar" subtitulo="Acesse com o e-mail cadastrado na sua igreja.">
      {(estado.aviso ?? avisoSessao) && (
        <p className="aviso sucesso" role="status">{estado.aviso ?? avisoSessao}</p>
      )}
      <form onSubmit={enviar} noValidate>
        <Campo
          rotulo="E-mail"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />
        <Campo
          rotulo="Senha"
          type="password"
          autoComplete="current-password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          required
        />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <button type="submit" className="botao" disabled={enviando || !email || !senha}>
          {enviando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
      <p className="rodape-cartao">
        <Link to="/esqueci-senha">Esqueci minha senha</Link>
      </p>
    </CartaoAuth>
  )
}
