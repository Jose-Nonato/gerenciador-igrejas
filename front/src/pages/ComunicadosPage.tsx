import { useState } from 'react'
import { Link } from 'react-router-dom'
import { comunicadosApi } from '../api/endpoints'
import type { CategoriaPost } from '../api/types'
import { Carregando } from '../components/Carregando'
import { formatarDataHora } from '../formatar'
import { CATEGORIA, rotuloPublico } from '../rotulos'
import { useAcessoSociedades } from '../useAcessoSociedades'
import { useCarga } from '../useCarga'

const POR_PAGINA = 10

export function ComunicadosPage() {
  const { gestor, temAcesso } = useAcessoSociedades()
  const [categoria, setCategoria] = useState<CategoriaPost | ''>('')
  const [pagina, setPagina] = useState(0)
  const { dados, erro, carregando } = useCarga(
    () => comunicadosApi.mural({ categoria: categoria || undefined, limit: POR_PAGINA, offset: pagina * POR_PAGINA }),
    [categoria, pagina],
  )

  const total = dados?.total ?? 0
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))

  return (
    <section className="pagina estreita-media">
      <div className="titulo-linha">
        <h1>Comunicados</h1>
        {(gestor || temAcesso) && (
          <Link to="/comunicados/gerenciar" className="botao secundario">Gerenciar comunicados</Link>
        )}
      </div>

      <div className="campo filtro-unico">
        <label htmlFor="f-categoria">Categoria</label>
        <select
          id="f-categoria"
          value={categoria}
          onChange={(e) => {
            setCategoria(e.target.value as CategoriaPost | '')
            setPagina(0)
          }}
        >
          <option value="">Todas</option>
          {Object.entries(CATEGORIA).map(([v, r]) => (
            <option key={v} value={v}>{r}</option>
          ))}
        </select>
      </div>

      {erro && !dados && <p className="aviso erro" role="alert">{erro}</p>}
      {!dados && !erro && <Carregando />}

      {dados && (
        <div aria-busy={carregando}>
          {dados.items.length === 0 ? (
            <p className="vazio-texto">Nenhum comunicado por enquanto.</p>
          ) : (
            <div className="mural">
              {dados.items.map((c) => (
                <article key={c.id} className="comunicado">
                  <div className="comunicado-topo">
                    <span className={`selo categoria-${c.categoria}`}>{CATEGORIA[c.categoria]}</span>
                    <span className="ajuda">{rotuloPublico(c)}</span>
                  </div>
                  <h2>{c.titulo}</h2>
                  <p className="comunicado-meta">
                    {formatarDataHora(c.data_publicacao)}
                    {c.autor ? ` · ${c.autor}` : ''}
                  </p>
                  <p className="comunicado-corpo">{c.corpo}</p>
                </article>
              ))}
            </div>
          )}

          {total > POR_PAGINA && (
            <div className="paginacao">
              <span>{total} comunicados</span>
              <div>
                <button type="button" className="botao secundario" disabled={pagina === 0 || carregando} onClick={() => setPagina((p) => p - 1)}>
                  Mais recentes
                </button>
                <span className="pagina-atual">Página {pagina + 1} de {paginas}</span>
                <button type="button" className="botao secundario" disabled={pagina + 1 >= paginas || carregando} onClick={() => setPagina((p) => p + 1)}>
                  Mais antigos
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
