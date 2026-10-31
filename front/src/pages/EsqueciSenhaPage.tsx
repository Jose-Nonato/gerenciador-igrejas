import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { authApi } from '../api/endpoints'
import { CartaoAuth } from '../components/CartaoAuth'
import { Campo } from '../components/Campo'

export function EsqueciSenhaPage() {
  const [email, setEmail] = useState('')
  const [enviado, setEnviado] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await authApi.esqueciSenha(email.trim())
      setEnviado(true)
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível enviar o pedido.')
    } finally {
      setEnviando(false)
    }
  }

  if (enviado) {
    return (
      <CartaoAuth titulo="Verifique seu e-mail">
        {/* O backend responde igual exista ou não o e-mail; a mensagem também não revela isso */}
        <p className="aviso sucesso" role="status">
          Se o e-mail estiver cadastrado, enviamos um link para redefinir a senha. Ele vale por 24 horas e só pode
          ser usado uma vez.
        </p>
        <p className="rodape-cartao">
          <Link to="/login">Voltar ao login</Link>
        </p>
      </CartaoAuth>
    )
  }

  return (
    <CartaoAuth titulo="Recuperar senha" subtitulo="Informe seu e-mail para receber o link de redefinição.">
      <form onSubmit={enviar} noValidate>
        <Campo
          rotulo="E-mail"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <button type="submit" className="botao" disabled={enviando || !email}>
          {enviando ? 'Enviando…' : 'Enviar link'}
        </button>
      </form>
      <p className="rodape-cartao">
        <Link to="/login">Voltar ao login</Link>
      </p>
    </CartaoAuth>
  )
}
