import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { authApi } from '../api/endpoints'
import { CartaoAuth } from '../components/CartaoAuth'
import { Campo } from '../components/Campo'

const MIN_SENHA = 8

/** Destino do link enviado por e-mail, tanto para convite quanto para redefinição. */
export function RedefinirSenhaPage() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const navegar = useNavigate()
  const [senha, setSenha] = useState('')
  const [confirma, setConfirma] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (!token) {
    return (
      <CartaoAuth titulo="Link inválido">
        <p className="aviso erro" role="alert">
          O link está incompleto. Use o endereço completo enviado por e-mail ou peça um novo.
        </p>
        <p className="rodape-cartao">
          <Link to="/esqueci-senha">Pedir novo link</Link>
        </p>
      </CartaoAuth>
    )
  }

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (senha.length < MIN_SENHA) return setErro(`A senha precisa ter ao menos ${MIN_SENHA} caracteres.`)
    if (senha !== confirma) return setErro('As senhas não conferem.')
    setErro(null)
    setEnviando(true)
    try {
      await authApi.redefinirSenha(token!, senha)
      navegar('/login', { replace: true, state: { aviso: 'Senha definida. Entre com a nova senha.' } })
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível redefinir a senha.')
      setEnviando(false)
    }
  }

  return (
    <CartaoAuth titulo="Definir nova senha">
      <form onSubmit={enviar} noValidate>
        <Campo
          rotulo="Nova senha"
          type="password"
          autoComplete="new-password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          ajuda={`Mínimo de ${MIN_SENHA} caracteres.`}
          required
          autoFocus
        />
        <Campo
          rotulo="Confirmar nova senha"
          type="password"
          autoComplete="new-password"
          value={confirma}
          onChange={(e) => setConfirma(e.target.value)}
          required
        />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <button type="submit" className="botao" disabled={enviando || !senha || !confirma}>
          {enviando ? 'Salvando…' : 'Salvar senha'}
        </button>
      </form>
    </CartaoAuth>
  )
}
