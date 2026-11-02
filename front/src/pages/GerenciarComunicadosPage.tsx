import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ApiError } from '../api/client'
import { comunicadosApi } from '../api/endpoints'
import type { CategoriaPost, Comunicado, StatusPost } from '../api/types'
import { Carregando } from '../components/Carregando'
import { DialogoConfirmar } from '../components/DialogoConfirmar'
import { PublicarComunicadoDialogo } from '../components/PublicarComunicadoDialogo'
import { formatarDataHora } from '../formatar'
import { CATEGORIA, STATUS_POST, rotuloPublico } from '../rotulos'
import { useCarga } from '../useCarga'

const POR_PAGINA = 15

function quando(c: Comunicado): string {
  if (c.status === 'rascunho') return '—'
  return `${c.status === 'agendado' ? 'Para ' : ''}${formatarDataHora(c.data_publicacao)}`
}

export function GerenciarComunicadosPage() {
  const avisoRota = (useLocation().state as { aviso?: string } | null)?.aviso
  const [status, setStatus] = useState<StatusPost | ''>('')
  const [categoria, setCategoria] = useState<CategoriaPost | ''>('')
  const [pagina, setPagina] = useState(0)
  const { dados, erro, carregando, recarregar } = useCarga(
    () =>
      comunicadosApi.gerenciar({
        status: status || undefined,
        categoria: categoria || undefined,
        limit: POR_PAGINA,
        offset: pagina * POR_PAGINA,
      }),
    [status, categoria, pagina],
  )
  const [avisoLocal, setAvisoLocal] = useState<string | null>(null)
  const aviso = avisoLocal ?? avisoRota
  const [erroAcao, setErroAcao] = useState<string | null>(null)
  const [publicando, setPublicando] = useState<Comunicado | null>(null)
  const [excluindo, setExcluindo] = useState<Comunicado | null>(null)
  const [ocupado, setOcupado] = useState(false)

  async function despublicar(c: Comunicado) {
    setErroAcao(null)
    try {
      await comunicadosApi.despublicar(c.id)
      setAvisoLocal(`"${c.titulo}" voltou para rascunho.`)
      recarregar()
    } catch (err) {
      setErroAcao(err instanceof ApiError ? err.message : 'Não foi possível despublicar.')
    }
  }

  async function excluir() {
    if (!excluindo) return
    setOcupado(true)
    setErroAcao(null)
    try {
      await comunicadosApi.excluir(excluindo.id)
      setAvisoLocal(`"${excluindo.titulo}" foi excluído.`)
      setExcluindo(null)
      // Excluiu o único item da última página: volta uma
      if (dados && dados.items.length === 1 && pagina > 0) setPagina((p) => p - 1)
      recarregar()
    } catch (err) {
      setErroAcao(err instanceof ApiError ? err.message : 'Não foi possível excluir.')
    } finally {
      setOcupado(false)
    }
  }

  if (erro && !dados) {
    return (
      <section className="pagina">
        <p className="aviso erro" role="alert">{erro}</p>
        <Link to="/comunicados">← Comunicados</Link>
      </section>
    )
  }
  if (!dados) return <Carregando />

  const total = dados.total
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))

  return (
    <section className="pagina">
      <p className="migalha">
        <Link to="/comunicados">← Comunicados</Link>
      </p>
      <div className="titulo-linha">
        <h1>Gerenciar comunicados</h1>
        <Link to="/comunicados/novo" className="botao">Novo comunicado</Link>
      </div>

      <div className="filtros">
        <div className="campo">
          <label htmlFor="g-status">Situação</label>
          <select
            id="g-status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as StatusPost | '')
              setPagina(0)
            }}
          >
            <option value="">Todas</option>
            {Object.entries(STATUS_POST).map(([v, r]) => (
              <option key={v} value={v}>{r}</option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="g-categoria">Categoria</label>
          <select
            id="g-categoria"
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
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}
      {(erroAcao || erro) && <p className="aviso erro" role="alert">{erroAcao ?? erro}</p>}

      <div className="tabela-wrap" aria-busy={carregando}>
        <table>
          <thead>
            <tr>
              <th>Título</th>
              <th>Categoria</th>
              <th>Público</th>
              <th>Situação</th>
              <th>Publicação</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {dados.items.map((c) => (
              <tr key={c.id}>
                <td className="titulo-celula">{c.titulo}</td>
                <td>{CATEGORIA[c.categoria]}</td>
                <td>{rotuloPublico(c)}</td>
                <td><span className={`selo post-${c.status}`}>{STATUS_POST[c.status]}</span></td>
                <td>{quando(c)}</td>
                <td className="acoes">
                  <Link to={`/comunicados/${c.id}/editar`} className="botao secundario pequeno" aria-label={`Editar ${c.titulo}`}>
                    Editar
                  </Link>
                  {c.status === 'rascunho' ? (
                    <button
                      type="button"
                      className="botao pequeno"
                      aria-label={`Publicar ${c.titulo}`}
                      onClick={() => {
                        setAvisoLocal(null)
                        setPublicando(c)
                      }}
                    >
                      Publicar
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="botao secundario pequeno"
                      aria-label={`${c.status === 'agendado' ? 'Cancelar agendamento de' : 'Despublicar'} ${c.titulo}`}
                      onClick={() => despublicar(c)}
                    >
                      {c.status === 'agendado' ? 'Cancelar agendamento' : 'Despublicar'}
                    </button>
                  )}
                  <button
                    type="button"
                    className="botao secundario pequeno"
                    aria-label={`Excluir ${c.titulo}`}
                    onClick={() => setExcluindo(c)}
                  >
                    Excluir
                  </button>
                </td>
              </tr>
            ))}
            {dados.items.length === 0 && (
              <tr>
                <td colSpan={6} className="vazio">Nenhum comunicado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="paginacao">
        <span>{total} {total === 1 ? 'comunicado' : 'comunicados'}</span>
        <div>
          <button type="button" className="botao secundario" disabled={pagina === 0 || carregando} onClick={() => setPagina((p) => p - 1)}>
            Anterior
          </button>
          <span className="pagina-atual">Página {pagina + 1} de {paginas}</span>
          <button type="button" className="botao secundario" disabled={pagina + 1 >= paginas || carregando} onClick={() => setPagina((p) => p + 1)}>
            Próxima
          </button>
        </div>
      </div>

      {publicando && (
        <PublicarComunicadoDialogo
          comunicado={publicando}
          onFechar={() => setPublicando(null)}
          onPublicado={(c) => {
            setAvisoLocal(
              c.status === 'agendado'
                ? `"${c.titulo}" agendado para ${formatarDataHora(c.publicar_em)}.`
                : `"${c.titulo}" publicado.`,
            )
            setPublicando(null)
            recarregar()
          }}
        />
      )}

      <DialogoConfirmar
        aberto={excluindo !== null}
        titulo="Excluir este comunicado?"
        rotuloConfirmar="Excluir comunicado"
        ocupado={ocupado}
        erro={erroAcao}
        onConfirmar={excluir}
        onCancelar={() => {
          setExcluindo(null)
          setErroAcao(null)
        }}
      >
        <p>
          <strong>{excluindo?.titulo}</strong> deixa de aparecer no mural e nesta lista. O registro fica guardado na
          auditoria.
        </p>
      </DialogoConfirmar>
    </section>
  )
}
