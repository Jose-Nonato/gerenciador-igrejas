import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { comunicadosApi } from '../api/endpoints'
import type { Comunicado } from '../api/types'
import { Campo } from './Campo'
import { Dialogo } from './Dialogo'

/** Valor para <input type="datetime-local"> (horário local), daqui a `minutos`. */
function localDaqui(minutos: number): string {
  const d = new Date(Date.now() + minutos * 60_000)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

interface Props {
  comunicado: Comunicado
  onPublicado: (c: Comunicado) => void
  onFechar: () => void
}

export function PublicarComunicadoDialogo({ comunicado, onPublicado, onFechar }: Props) {
  const [agendar, setAgendar] = useState(false)
  const [quando, setQuando] = useState(() => localDaqui(60))
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (agendar) {
      if (!quando) return setErro('Informe a data e a hora.')
      if (new Date(quando).getTime() <= Date.now()) return setErro('Escolha um horário no futuro, ou publique agora.')
    }
    setErro(null)
    setEnviando(true)
    try {
      // O horário digitado é local; o backend recebe um instante com fuso (UTC)
      onPublicado(await comunicadosApi.publicar(comunicado.id, agendar ? new Date(quando).toISOString() : undefined))
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível publicar.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Publicar comunicado" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <p className="dialogo-texto">
          <strong>{comunicado.titulo}</strong>
        </p>
        <fieldset className="opcoes">
          <legend className="sr-only">Quando publicar</legend>
          <label className="opcao">
            <input type="radio" name="quando" checked={!agendar} onChange={() => setAgendar(false)} />
            Publicar agora
          </label>
          <label className="opcao">
            <input type="radio" name="quando" checked={agendar} onChange={() => setAgendar(true)} />
            Agendar para depois
          </label>
        </fieldset>
        {agendar && (
          <Campo
            rotulo="Data e hora"
            type="datetime-local"
            min={localDaqui(0)}
            value={quando}
            onChange={(e) => setQuando(e.target.value)}
            ajuda="Aparece no mural a partir desse horário (no fuso do seu navegador)."
          />
        )}
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Salvando…' : agendar ? 'Agendar' : 'Publicar agora'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}
