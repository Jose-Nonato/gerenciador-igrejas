import { useEffect, useRef, type ReactNode } from 'react'

interface Props {
  aberto: boolean
  titulo: string
  children: ReactNode
  rotuloConfirmar: string
  rotuloOcupado?: string
  ocupado?: boolean
  erro?: string | null
  onConfirmar: () => void
  onCancelar: () => void
}

/** Confirmação de ação destrutiva sobre o <dialog> nativo (foco preso e Esc fechando). */
export function DialogoConfirmar({
  aberto,
  titulo,
  children,
  rotuloConfirmar,
  rotuloOcupado = 'Excluindo…',
  ocupado = false,
  erro,
  onConfirmar,
  onCancelar,
}: Props) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dlg = ref.current
    if (!dlg) return
    if (aberto && !dlg.open) dlg.showModal()
    if (!aberto && dlg.open) dlg.close()
  }, [aberto])

  return (
    <dialog
      ref={ref}
      className="dialogo"
      aria-labelledby="dialogo-titulo"
      onCancel={(e) => {
        e.preventDefault() // o estado `aberto` é quem manda
        if (!ocupado) onCancelar()
      }}
    >
      <h2 id="dialogo-titulo">{titulo}</h2>
      <div className="dialogo-corpo">{children}</div>
      {erro && <p className="aviso erro" role="alert">{erro}</p>}
      <div className="acoes-form">
        <button type="button" className="botao perigo" onClick={onConfirmar} disabled={ocupado}>
          {ocupado ? rotuloOcupado : rotuloConfirmar}
        </button>
        <button type="button" className="botao secundario" onClick={onCancelar} disabled={ocupado}>
          Cancelar
        </button>
      </div>
    </dialog>
  )
}
