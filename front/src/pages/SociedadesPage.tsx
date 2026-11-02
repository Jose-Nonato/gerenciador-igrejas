import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { sociedadesApi } from '../api/endpoints'
import type { Sociedade } from '../api/types'
import { Carregando } from '../components/Carregando'
import { NovaSociedadeDialogo } from '../components/NovaSociedadeDialogo'
import { SIGLA, SIGLAS } from '../rotulos'

export function SociedadesPage() {
  const [sociedades, setSociedades] = useState<Sociedade[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [criando, setCriando] = useState(false)

  useEffect(() => {
    let ativo = true
    sociedadesApi
      .listar()
      .then((lista) => ativo && setSociedades(lista))
      .catch((err) => ativo && setErro(err instanceof ApiError ? err.message : 'Falha ao carregar as sociedades.'))
    return () => {
      ativo = false
    }
  }, [])

  if (erro) return <p className="aviso erro" role="alert">{erro}</p>
  if (!sociedades) return <Carregando />

  const existentes = new Set(sociedades.map((s) => s.sigla))
  const disponiveis = SIGLAS.filter((s) => !existentes.has(s))

  return (
    <section className="pagina">
      <div className="titulo-linha">
        <h1>Sociedades internas</h1>
        {disponiveis.length > 0 && (
          <button type="button" className="botao" onClick={() => setCriando(true)}>
            Nova sociedade
          </button>
        )}
      </div>

      {sociedades.length === 0 ? (
        <p className="vazio-texto">Nenhuma sociedade criada ainda. Comece criando a primeira.</p>
      ) : (
        <div className="atalhos">
          {sociedades.map((s) => (
            <Link key={s.id} to={`/sociedades/${s.id}`} className="atalho">
              <strong>{s.sigla}{s.nome ? ` — ${s.nome}` : ''}</strong>
              <span>{SIGLA[s.sigla]}</span>
              <span>{s.total_socios} {s.total_socios === 1 ? 'sócio' : 'sócios'}</span>
            </Link>
          ))}
        </div>
      )}

      {criando && (
        <NovaSociedadeDialogo
          disponiveis={disponiveis}
          onFechar={() => setCriando(false)}
          onCriada={(nova) => {
            setSociedades((atuais) => [...(atuais ?? []), nova].sort((a, b) => a.sigla.localeCompare(b.sigla)))
            setCriando(false)
          }}
        />
      )}
    </section>
  )
}
