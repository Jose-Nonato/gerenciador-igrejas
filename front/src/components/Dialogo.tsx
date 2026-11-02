import { useEffect, useId, useRef, type ReactNode } from 'react'

interface Props {
  titulo: string
  onFechar: () => void
  children: ReactNode
}

/**
 * Janela modal sobre o <dialog> nativo (foco preso, Esc fecha).
 * O pai a monta só quando precisa dela; ao desmontar, o estado do formulário some junto.
 */
export function Dialogo({ titulo, onFechar, children }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const tituloId = useId()

  useEffect(() => {
    const dlg = ref.current
    if (dlg && !dlg.open) dlg.showModal()
  }, [])

  return (
    <dialog
      ref={ref}
      className="dialogo largo"
      aria-labelledby={tituloId}
      onCancel={(e) => {
        e.preventDefault() // quem decide fechar é o pai (desmontando o componente)
        onFechar()
      }}
    >
      <h2 id={tituloId}>{titulo}</h2>
      {children}
    </dialog>
  )
}
