import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { sociedadesApi } from '../api/endpoints'
import type { ItemPresenca, ReuniaoDetalhe, Sociedade, Socio, StatusPresenca } from '../api/types'
import { Campo } from '../components/Campo'
import { Carregando } from '../components/Carregando'
import { formatarData } from '../formatar'
import { STATUS_PRESENCA, TIPO_SOCIO } from '../rotulos'
import { useCarga } from '../useCarga'

const hoje = () => new Date().toISOString().slice(0, 10)
const STATUS: StatusPresenca[] = ['P', 'A', 'J']

interface Linha {
  socioId: string
  nome: string
  detalhe: string
}

/** Sócios ativos mais quem já tem presença nesta reunião (inclusive quem saiu depois). */
function montarLinhas(socios: Socio[], reuniao: ReuniaoDetalhe | null): Linha[] {
  const linhas: Linha[] = socios.map((s) => ({ socioId: s.id, nome: s.nome, detalhe: TIPO_SOCIO[s.tipo] }))
  const conhecidos = new Set(linhas.map((l) => l.socioId))
  for (const p of reuniao?.presencas ?? []) {
    if (!conhecidos.has(p.socio_id)) linhas.push({ socioId: p.socio_id, nome: p.nome, detalhe: 'Já saiu da sociedade' })
  }
  return linhas
}

interface FormProps {
  sociedade: Sociedade
  reuniao: ReuniaoDetalhe | null
  socios: Socio[]
}

function FormularioReuniao({ sociedade, reuniao, socios }: FormProps) {
  const navegar = useNavigate()
  const linhas = montarLinhas(socios, reuniao)
  const originais: Record<string, StatusPresenca> = Object.fromEntries(
    (reuniao?.presencas ?? []).map((p) => [p.socio_id, p.status]),
  )

  const [data, setData] = useState(reuniao?.data ?? hoje())
  const [tema, setTema] = useState(reuniao?.tema ?? '')
  const [marcas, setMarcas] = useState<Record<string, StatusPresenca>>(originais)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const lancados = linhas.filter((l) => marcas[l.socioId]).length
  const resumo = STATUS.map((st) => ({
    st,
    n: linhas.filter((l) => marcas[l.socioId] === st).length,
  }))

  function marcar(socioId: string, status: StatusPresenca) {
    setMarcas((atuais) => ({ ...atuais, [socioId]: status }))
  }

  function marcarTodosPresentes() {
    setMarcas((atuais) => {
      const novo = { ...atuais }
      for (const l of linhas) novo[l.socioId] ??= 'P' // só quem ainda não tem marca
      return novo
    })
  }

  async function salvar(e: FormEvent) {
    e.preventDefault()
    if (!data) return setErro('Informe a data da reunião.')
    if (data > hoje()) return setErro('A data da reunião não pode estar no futuro.')

    setErro(null)
    setEnviando(true)
    try {
      const temaLimpo = tema.trim() || null
      if (reuniao === null) {
        const presencas: ItemPresenca[] = Object.entries(marcas).map(([socio_id, status]) => ({ socio_id, status }))
        const criada = await sociedadesApi.criarReuniao(sociedade.id, { data, tema: temaLimpo, presencas })
        navegar(`/sociedades/${sociedade.id}?aba=reunioes`, {
          replace: true,
          state: { aviso: `Reunião de ${formatarData(criada.data)} registrada.` },
        })
        return
      }

      if (data !== reuniao.data || temaLimpo !== reuniao.tema) {
        await sociedadesApi.atualizarReuniao(sociedade.id, reuniao.id, { data, tema: temaLimpo })
      }
      // Só o que mudou em relação ao que já estava lançado
      const alteradas: ItemPresenca[] = Object.entries(marcas)
        .filter(([socio_id, status]) => originais[socio_id] !== status)
        .map(([socio_id, status]) => ({ socio_id, status }))
      if (alteradas.length > 0) await sociedadesApi.lancarPresencas(sociedade.id, reuniao.id, alteradas)

      navegar(`/sociedades/${sociedade.id}?aba=reunioes`, {
        replace: true,
        state: { aviso: `Reunião de ${formatarData(data)} atualizada.` },
      })
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar a reunião.')
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={salvar} noValidate>
      <div className="grade">
        <Campo rotulo="Data *" type="date" max={hoje()} value={data} onChange={(e) => setData(e.target.value)} required />
        <Campo rotulo="Tema" value={tema} onChange={(e) => setTema(e.target.value)} maxLength={255} />
      </div>

      <div className="titulo-linha">
        <h2 className="subtitulo-h2">Presença</h2>
        <button type="button" className="botao secundario pequeno" onClick={marcarTodosPresentes} disabled={linhas.length === 0}>
          Marcar quem falta como presente
        </button>
      </div>

      {linhas.length === 0 ? (
        <p className="vazio-texto">
          Esta sociedade ainda não tem sócios. <Link to={`/sociedades/${sociedade.id}`}>Cadastre os sócios</Link> para
          lançar presença.
        </p>
      ) : (
        <>
          <p className="ajuda" aria-live="polite">
            {lancados} de {linhas.length} lançados ·{' '}
            {resumo.map((r) => `${STATUS_PRESENCA[r.st]}: ${r.n}`).join(' · ')}. Quem ficar sem marca não recebe
            lançamento.
          </p>
          <div className="tabela-wrap">
            <table>
              <thead>
                <tr>
                  <th>Sócio</th>
                  <th>Presença</th>
                </tr>
              </thead>
              <tbody>
                {linhas.map((l) => (
                  <tr key={l.socioId}>
                    <td>
                      {l.nome}
                      <br />
                      <small className="ajuda">{l.detalhe}</small>
                    </td>
                    <td>
                      <div role="radiogroup" aria-label={`Presença de ${l.nome}`} className="segmentado">
                        {STATUS.map((st) => (
                          <label key={st} className={marcas[l.socioId] === st ? `seg ativo st-${st}` : 'seg'} title={STATUS_PRESENCA[st]}>
                            <input
                              type="radio"
                              name={`presenca-${l.socioId}`}
                              value={st}
                              checked={marcas[l.socioId] === st}
                              onChange={() => marcar(l.socioId, st)}
                            />
                            <span aria-hidden="true">{st}</span>
                            <span className="sr-only">{STATUS_PRESENCA[st]}</span>
                          </label>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {erro && <p className="aviso erro" role="alert">{erro}</p>}
      <div className="acoes-form acoes-topo">
        <button type="submit" className="botao" disabled={enviando}>
          {enviando ? 'Salvando…' : reuniao === null ? 'Registrar reunião' : 'Salvar alterações'}
        </button>
        <Link to={`/sociedades/${sociedade.id}?aba=reunioes`} className="botao secundario">Cancelar</Link>
      </div>
    </form>
  )
}

export function ReuniaoPage() {
  const { id = '', reuniaoId } = useParams<{ id: string; reuniaoId: string }>()
  const sociedade = useCarga(() => sociedadesApi.obter(id), [id])
  const socios = useCarga(() => sociedadesApi.socios(id), [id])
  const reuniao = useCarga<ReuniaoDetalhe | null>(
    () => (reuniaoId ? sociedadesApi.reuniao(id, reuniaoId) : Promise.resolve(null)),
    [id, reuniaoId],
  )

  const erro = sociedade.erro ?? socios.erro ?? reuniao.erro
  if (erro) {
    return (
      <section className="pagina">
        <p className="aviso erro" role="alert">{erro}</p>
        <Link to={`/sociedades/${id}?aba=reunioes`}>← Voltar</Link>
      </section>
    )
  }
  if (!sociedade.dados || !socios.dados || reuniao.dados === undefined) return <Carregando />

  return (
    <section className="pagina estreita-media">
      <p className="migalha">
        <Link to={`/sociedades/${id}?aba=reunioes`}>← {sociedade.dados.sigla}: reuniões</Link>
      </p>
      <h1>{reuniaoId ? 'Reunião' : 'Nova reunião'}</h1>
      <FormularioReuniao
        key={reuniaoId ?? 'nova'}
        sociedade={sociedade.dados}
        socios={socios.dados}
        reuniao={reuniao.dados}
      />
    </section>
  )
}
