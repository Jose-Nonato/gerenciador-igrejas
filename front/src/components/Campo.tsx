import { useId, type InputHTMLAttributes } from 'react'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  rotulo: string
  ajuda?: string
}

export function Campo({ rotulo, ajuda, id, ...resto }: Props) {
  const gerado = useId()
  const campoId = id ?? gerado
  return (
    <div className="campo">
      <label htmlFor={campoId}>{rotulo}</label>
      <input id={campoId} aria-describedby={ajuda ? `${campoId}-ajuda` : undefined} {...resto} />
      {ajuda && (
        <small id={`${campoId}-ajuda`} className="ajuda">
          {ajuda}
        </small>
      )}
    </div>
  )
}
