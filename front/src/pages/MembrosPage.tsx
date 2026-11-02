import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ApiError } from '../api/client'
import { membrosApi } from '../api/endpoints'
import type { FiltroMembros, Membro, MembroPage, Rol, SituacaoMembro } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { DialogoConfirmar } from '../components/DialogoConfirmar'
import { podeExcluirMembro } from '../permissoes'
import { OFICIO, ROL, SITUACAO } from '../rotulos'

const POR_PAGINA = 20

function formatarData(iso: string | null): string {
  if (!iso) return '—'
  const [a, m, d] = iso.split('-')
  return `${d}/${m}/${a}`
}

export function MembrosPage() {
  const avisoRota = (useLocation().state as { aviso?: string } | null)?.aviso
  const { usuario } = useAuth()
  const podeExcluir = podeExcluirMembro(usuario)
  const [avisoLocal, setAvisoLocal] = useState<string | null>(null)
  const aviso = avisoLocal ?? avisoRota
  const [versao, setVersao] = useState(0) // muda depois de excluir, para recarregar a lista
  const [alvo, setAlvo] = useState<Membro | null>(null)
  const [excluindo, setExcluindo] = useState(false)
  const [erroExclusao, setErroExclusao] = useState<string | null>(null)
  const [busca, setBusca] = useState('')
  const [q, setQ] = useState('')
  const [rol, setRol] = useState<Rol | ''>('')
  const [situacao, setSituacao] = useState<SituacaoMembro | ''>('')
  const [pagina, setPagina] = useState(0)
  const [resultado, setResultado] = useState<{ chave: string; dados?: MembroPage; erro?: string } | null>(null)
  const [erroExportar, setErroExportar] = useState<string | null>(null)
  const [exportando, setExportando] = useState(false)

  // Espera o usuário parar de digitar antes de consultar o backend
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(busca.trim())
      setPagina(0)
    }, 300)
    return () => clearTimeout(t)
  }, [busca])

  const filtro: FiltroMembros = {
    q: q || undefined,
    rol: rol || undefined,
    situacao: situacao || undefined,
  }

  // Carregando = o resultado guardado ainda é de outra consulta
  const chave = JSON.stringify([q, rol, situacao, pagina, versao])
  const carregando = resultado?.chave !== chave
  const dados = resultado?.dados ?? null
  const erro = (resultado?.chave === chave ? resultado.erro : undefined) ?? erroExportar

  useEffect(() => {
    let ativo = true
    membrosApi
      .listar({ q: q || undefined, rol: rol || undefined, situacao: situacao || undefined, limit: POR_PAGINA, offset: pagina * POR_PAGINA })
      .then((res) => ativo && setResultado({ chave, dados: res }))
      .catch((err) =>
        ativo &&
        setResultado((r) => ({
          chave,
          dados: r?.dados,
          erro: err instanceof ApiError ? err.message : 'Falha ao carregar o rol.',
        })),
      )
    return () => {
      ativo = false
    }
  }, [chave, q, rol, situacao, pagina])

  async function excluir() {
    if (!alvo) return
    setExcluindo(true)
    setErroExclusao(null)
    try {
      await membrosApi.excluir(alvo.id)
      setAvisoLocal(`${alvo.nome} foi excluído(a) do rol.`)
      setAlvo(null)
      // Excluiu o único item da última página: volta uma página
      if (dados && dados.items.length === 1 && pagina > 0) setPagina((p) => p - 1)
      setVersao((v) => v + 1)
    } catch (err) {
      setErroExclusao(err instanceof ApiError ? err.message : 'Não foi possível excluir o membro.')
    } finally {
      setExcluindo(false)
    }
  }

  async function exportar() {
    setExportando(true)
    setErroExportar(null)
    try {
      const blob = await membrosApi.exportarCsv(filtro)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'rol.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setErroExportar(err instanceof ApiError ? err.message : 'Falha ao exportar.')
    } finally {
      setExportando(false)
    }
  }

  const total = dados?.total ?? 0
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))

  return (
    <section className="pagina">
      <div className="titulo-linha">
        <h1>Rol de membros</h1>
        <div className="acoes-form">
          <button type="button" className="botao secundario" onClick={exportar} disabled={exportando}>
            {exportando ? 'Exportando…' : 'Exportar CSV'}
          </button>
          <Link to="/membros/novo" className="botao">Adicionar membro</Link>
        </div>
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}

      <div className="filtros">
        <div className="campo">
          <label htmlFor="busca">Buscar por nome</label>
          <input id="busca" type="search" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="f-rol">Rol</label>
          <select
            id="f-rol"
            value={rol}
            onChange={(e) => {
              setRol(e.target.value as Rol | '')
              setPagina(0)
            }}
          >
            <option value="">Todos</option>
            {Object.entries(ROL).map(([v, r]) => (
              <option key={v} value={v}>{r}</option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="f-sit">Situação</label>
          <select
            id="f-sit"
            value={situacao}
            onChange={(e) => {
              setSituacao(e.target.value as SituacaoMembro | '')
              setPagina(0)
            }}
          >
            <option value="">Todas</option>
            {Object.entries(SITUACAO).map(([v, r]) => (
              <option key={v} value={v}>{r}</option>
            ))}
          </select>
        </div>
      </div>

      {erro && <p className="aviso erro" role="alert">{erro}</p>}

      <div className="tabela-wrap" aria-busy={carregando}>
        <table>
          <thead>
            <tr>
              <th>Nº</th>
              <th>Nome</th>
              <th>Rol</th>
              <th>Situação</th>
              <th>Ofício</th>
              <th>Nascimento</th>
              <th>Telefone</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {dados?.items.map((m) => (
              <tr key={m.id}>
                <td>{m.numero_rol ?? '—'}</td>
                <td>{m.nome}</td>
                <td>{ROL[m.rol]}</td>
                <td><span className={`selo ${m.situacao}`}>{SITUACAO[m.situacao]}</span></td>
                <td>{OFICIO[m.oficio]}</td>
                <td>{formatarData(m.data_nascimento)}</td>
                <td>{m.telefone ?? '—'}</td>
                <td className="acoes">
                  <Link to={`/membros/${m.id}/editar`} className="botao secundario pequeno" aria-label={`Editar ${m.nome}`}>
                    Editar
                  </Link>
                  {podeExcluir && (
                    <button
                      type="button"
                      className="botao secundario pequeno"
                      aria-label={`Excluir ${m.nome}`}
                      onClick={() => setAlvo(m)}
                    >
                      Excluir
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {dados && dados.items.length === 0 && (
              <tr>
                <td colSpan={8} className="vazio">Nenhum membro encontrado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="paginacao">
        <span>{total} {total === 1 ? 'membro' : 'membros'}</span>
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

      <DialogoConfirmar
        aberto={alvo !== null}
        titulo="Excluir este membro?"
        rotuloConfirmar="Excluir membro"
        ocupado={excluindo}
        erro={erroExclusao}
        onConfirmar={excluir}
        onCancelar={() => {
          setAlvo(null)
          setErroExclusao(null)
        }}
      >
        <p>
          <strong>{alvo?.nome}</strong> (nº {alvo?.numero_rol ?? '—'}) será removido(a) do rol. Use para cadastros
          feitos por engano; para transferência ou falecimento, registre o evento eclesiástico. O histórico fica
          preservado.
        </p>
      </DialogoConfirmar>
    </section>
  )
}
