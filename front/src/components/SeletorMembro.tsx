import { useEffect, useId, useState } from 'react'
import { membrosApi } from '../api/endpoints'
import type { Membro } from '../api/types'

interface Props {
  /** Membro vinculado agora (null = nenhum) */
  nomeSelecionado: string | null
  onSelecionar: (membro: Membro | null) => void
}

/** Escolha de membro por busca de nome (o rol pode ter centenas de pessoas). */
export function SeletorMembro({ nomeSelecionado, onSelecionar }: Props) {
  const inputId = useId()
  const [busca, setBusca] = useState('')
  const [q, setQ] = useState('')
  const [resultado, setResultado] = useState<{ q: string; itens: Membro[]; falhou: boolean } | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setQ(busca.trim()), 300)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    if (q.length < 2) return
    let ativo = true
    membrosApi
      .listar({ q, limit: 8 })
      .then((res) => ativo && setResultado({ q, itens: res.items, falhou: false }))
      .catch(() => ativo && setResultado({ q, itens: [], falhou: true }))
    return () => {
      ativo = false
    }
  }, [q])

  const mostrando = q.length >= 2 ? resultado : null
  const buscando = q.length >= 2 && resultado?.q !== q

  return (
    <div className="campo">
      <label htmlFor={inputId}>Membro vinculado</label>
      <p className="atual">
        {nomeSelecionado ? (
          <>
            <strong>{nomeSelecionado}</strong>{' '}
            <button type="button" className="link" onClick={() => onSelecionar(null)}>
              Remover vínculo
            </button>
          </>
        ) : (
          <span className="ajuda">Nenhum membro vinculado.</span>
        )}
      </p>
      <input
        id={inputId}
        type="search"
        placeholder="Buscar membro pelo nome (mín. 2 letras)"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        autoComplete="off"
      />
      {buscando && <small className="ajuda">Buscando…</small>}
      {mostrando?.falhou && <small className="ajuda">Não foi possível buscar agora.</small>}
      {mostrando && !buscando && !mostrando.falhou && mostrando.itens.length === 0 && (
        <small className="ajuda">Nenhum membro encontrado.</small>
      )}
      {mostrando && !buscando && mostrando.itens.length > 0 && (
        <ul className="resultados" aria-label="Resultados da busca">
          {mostrando.itens.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                onClick={() => {
                  onSelecionar(m)
                  setBusca('')
                  setQ('')
                  setResultado(null)
                }}
              >
                {m.nome} <span className="ajuda">(nº {m.numero_rol ?? '—'})</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
