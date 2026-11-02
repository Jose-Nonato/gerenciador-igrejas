import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { usuariosApi } from '../api/endpoints'
import type { Membro, Perfil, Usuario } from '../api/types'
import { PERFIL } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'
import { Dialogo } from './Dialogo'

interface Props {
  membro: Membro
  onConvidado: (usuario: Usuario) => void
  onFechar: () => void
}

/** Convida o membro para acessar o sistema: a conta já nasce ligada a ele. */
export function ConvidarMembroDialogo({ membro, onConvidado, onFechar }: Props) {
  const [email, setEmail] = useState(membro.email ?? '')
  const [perfil, setPerfil] = useState<Perfil>('usuario')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!email.trim()) return setErro('Informe o e-mail para onde enviar o convite.')
    setErro(null)
    setEnviando(true)
    try {
      onConvidado(await usuariosApi.convidar(email.trim(), perfil, membro.id))
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível enviar o convite.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Convidar para acessar o sistema" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <p className="dialogo-texto">
          <strong>{membro.nome}</strong> receberá um link por e-mail para criar a própria senha. A conta fica ligada a
          este membro.
        </p>
        <Campo
          rotulo="E-mail do convite"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="off"
          autoFocus
          ajuda={membro.email ? 'Veio do cadastro do membro; pode ser trocado.' : 'O membro não tem e-mail cadastrado.'}
        />
        <CampoSelect
          rotulo="Perfil"
          value={perfil}
          onChange={(e) => setPerfil(e.target.value as Perfil)}
          ajuda="Usuário comum só vê o que for do público dele; os demais perfis dão mais acesso."
        >
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
