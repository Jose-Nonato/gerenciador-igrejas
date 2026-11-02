import { useId, type ReactNode, type SelectHTMLAttributes } from 'react'

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  rotulo: string
  ajuda?: string
  children: ReactNode
}

export function CampoSelect({ rotulo, ajuda, id, children, ...resto }: Props) {
  const gerado = useId()
  const campoId = id ?? gerado
  return (
    <div className="campo">
      <label htmlFor={campoId}>{rotulo}</label>
      <select id={campoId} aria-describedby={ajuda ? `${campoId}-ajuda` : undefined} {...resto}>
        {children}
      </select>
      {ajuda && (
        <small id={`${campoId}-ajuda`} className="ajuda">
          {ajuda}
        </small>
      )}
    </div>
  )
}
