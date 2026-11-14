import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { Dialogo } from './Dialogo'

interface Props {
  titulo: string
  texto: string
  rotuloConfirmar: string
  /** Recebe o motivo (ou null, se ficou em branco). Deve lançar em caso de falha. */
  onConfirmar: (justificativa: string | null) => Promise<void>
  onFechar: () => void
}

/** Pede um motivo opcional antes de recusar ou cancelar um atendimento. */
export function JustificativaDialogo({ titulo, texto, rotuloConfirmar, onConfirmar, onFechar }: Props) {
  const [motivo, setMotivo] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await onConfirmar(motivo.trim() || null)
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível concluir a ação.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo={titulo} onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <p>{texto}</p>
        <div className="campo">
          <label htmlFor="j-motivo">Motivo (opcional)</label>
          <textarea id="j-motivo" rows={3} value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={500} autoFocus />
          <small className="ajuda">O motivo é mostrado à outra pessoa.</small>
        </div>
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao perigo" disabled={enviando}>
            {enviando ? 'Enviando…' : rotuloConfirmar}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Voltar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}
