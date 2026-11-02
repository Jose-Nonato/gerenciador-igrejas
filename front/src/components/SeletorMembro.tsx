import { useEffect, useId, useState } from 'react'
import { membrosApi } from '../api/endpoints'
import type { MembroResumo } from '../api/types'

interface Props {
  /** Membro escolhido agora (null = nenhum) */
  nomeSelecionado: string | null
  onSelecionar: (membro: MembroResumo | null) => void
  rotulo?: string
  /**
   * Como buscar. Por padrão usa a busca do rol (admin, pastor e presbítero). Quem não tem
   * acesso ao rol, como o líder de uma sociedade, passa uma busca restrita.
   */
  buscar?: (q: string) => Promise<MembroResumo[]>
}

const buscarNoRol = (q: string): Promise<MembroResumo[]> =>
  membrosApi.listar({ q, limit: 8 }).then((res) => res.items)

/** Escolha de membro por busca de nome (o rol pode ter centenas de pessoas). */
export function SeletorMembro({ nomeSelecionado, onSelecionar, rotulo = 'Membro vinculado', buscar = buscarNoRol }: Props) {
  const inputId = useId()
  const [busca, setBusca] = useState('')
  const [q, setQ] = useState('')
  const [resultado, setResultado] = useState<{ q: string; itens: MembroResumo[]; falhou: boolean } | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setQ(busca.trim()), 300)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    if (q.length < 2) return
    let ativo = true
    buscar(q)
      .then((itens) => ativo && setResultado({ q, itens, falhou: false }))
      .catch(() => ativo && setResultado({ q, itens: [], falhou: true }))
    return () => {
      ativo = false
    }
    // a função de busca não muda durante a vida do componente; `q` é quem dispara a consulta
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q])

  const mostrando = q.length >= 2 ? resultado : null
  const buscando = q.length >= 2 && resultado?.q !== q

  return (
    <div className="campo">
      <label htmlFor={inputId}>{rotulo}</label>
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
