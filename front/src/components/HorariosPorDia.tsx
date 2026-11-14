import { useMemo } from 'react'
import type { Horario } from '../api/types'
import { diaPorExtenso, horaCurta } from '../formatar'

interface Props {
  horarios: Horario[]
  onEscolher: (horario: Horario) => void
  /** Horário já escolhido (ganha destaque) */
  escolhido?: string | null
}

/** Horários livres agrupados por dia, um botão por horário. */
export function HorariosPorDia({ horarios, onEscolher, escolhido }: Props) {
  const porDia = useMemo(() => {
    const grupos = new Map<string, Horario[]>()
    for (const h of horarios) {
      const chave = diaPorExtenso(h.inicio)
      grupos.set(chave, [...(grupos.get(chave) ?? []), h])
    }
    return [...grupos.entries()]
  }, [horarios])

  return (
    <div>
      {porDia.map(([titulo, lista]) => (
        <div key={titulo} className="campo">
          <strong style={{ textTransform: 'capitalize' }}>{titulo}</strong>
          <div className="acoes-form">
            {lista.map((h) => (
              <button
                key={h.inicio}
                type="button"
                className={escolhido === h.inicio ? 'botao' : 'botao secundario'}
                aria-pressed={escolhido === h.inicio}
                onClick={() => onEscolher(h)}
              >
                {horaCurta(h.inicio)}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
