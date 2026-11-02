import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { usuariosApi } from '../api/endpoints'
import type { Perfil, Usuario } from '../api/types'
import { PERFIL } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'
import { Dialogo } from './Dialogo'

interface Props {
  onConvidado: (usuario: Usuario) => void
  onFechar: () => void
}

export function ConvidarUsuarioDialogo({ onConvidado, onFechar }: Props) {
  const [email, setEmail] = useState('')
  const [perfil, setPerfil] = useState<Perfil>('usuario')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!email.trim()) return setErro('Informe o e-mail do convidado.')
    setErro(null)
    setEnviando(true)
    try {
      onConvidado(await usuariosApi.convidar(email.trim(), perfil))
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível enviar o convite.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Convidar usuário" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <p className="ajuda dialogo-texto">
          A pessoa recebe um link por e-mail para definir a própria senha. O link vale por 24 horas.
        </p>
        <Campo
          rotulo="E-mail"
          type="email"
          autoComplete="off"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />
        <CampoSelect rotulo="Perfil" value={perfil} onChange={(e) => setPerfil(e.target.value as Perfil)}>
          {Object.entries(PERFIL).map(([v, r]) => (
            <option key={v} value={v}>{r}</option>
          ))}
        </CampoSelect>
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Enviando…' : 'Enviar convite'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}
