import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { authApi } from '../api/endpoints'
import { useAuth } from '../auth/useAuth'
import { Campo } from '../components/Campo'

const MIN_SENHA = 8

export function TrocarSenhaPage() {
  const { usuario, logout, descartarSessao } = useAuth()
  const navegar = useNavigate()
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  const [confirma, setConfirma] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const obrigatoria = usuario?.troca_obrigatoria ?? false

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (nova.length < MIN_SENHA) return setErro(`A nova senha precisa ter ao menos ${MIN_SENHA} caracteres.`)
    if (nova !== confirma) return setErro('As senhas não conferem.')
    setErro(null)
    setEnviando(true)
    try {
      await authApi.trocarSenha(atual, nova)
      // O backend encerra todas as sessões ao trocar a senha: é preciso entrar de novo.
      // O aviso vai pelo contexto: o RequireAuth redireciona para /login assim que a sessão cai.
      descartarSessao('Senha alterada. Entre com a nova senha.')
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível alterar a senha.')
      setEnviando(false)
    }
  }

  async function sair() {
    await logout()
    navegar('/login', { replace: true })
  }

  const formulario = (
    <form onSubmit={enviar} noValidate className="formulario">
      <Campo
        rotulo="Senha atual"
        type="password"
        autoComplete="current-password"
        value={atual}
        onChange={(e) => setAtual(e.target.value)}
        required
        autoFocus
      />
      <Campo
        rotulo="Nova senha"
        type="password"
        autoComplete="new-password"
        value={nova}
        onChange={(e) => setNova(e.target.value)}
        ajuda={`Mínimo de ${MIN_SENHA} caracteres, diferente da atual.`}
        required
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
      <button type="submit" className="botao" disabled={enviando || !atual || !nova || !confirma}>
        {enviando ? 'Salvando…' : 'Alterar senha'}
      </button>
    </form>
  )

  // Troca obrigatória: tela cheia, sem menu (o backend recusa qualquer outra rota até a troca)
  if (obrigatoria) {
    return (
      <main className="auth-pagina">
        <section className="auth-cartao">
          <p className="marca">Gerenciador de Igrejas</p>
          <h1>Defina uma nova senha</h1>
          <p className="subtitulo">Por segurança, você precisa trocar a senha provisória antes de continuar.</p>
          {formulario}
          <p className="rodape-cartao">
            <button type="button" className="link" onClick={sair}>
              Sair
            </button>
          </p>
        </section>
      </main>
    )
  }

  return (
    <section className="pagina estreita">
      <h1>Alterar senha</h1>
      {formulario}
    </section>
  )
}
