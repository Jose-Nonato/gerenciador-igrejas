import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { ebdApi } from '../api/endpoints'
import type { EbdAluno, EbdAulaDetalhe, EbdClasse, EbdItemPresenca, StatusPresenca } from '../api/types'
import { Campo } from '../components/Campo'
import { Carregando } from '../components/Carregando'
import { formatarData, hojeLocal } from '../formatar'
import { STATUS_PRESENCA } from '../rotulos'
import { useCarga } from '../useCarga'

const STATUS: StatusPresenca[] = ['P', 'A', 'J']

interface Linha {
  alunoId: string
  nome: string
  detalhe: string
}

/** Alunos ativos mais quem já tem presença nesta aula (inclusive quem saiu depois). */
function montarLinhas(alunos: EbdAluno[], aula: EbdAulaDetalhe | null): Linha[] {
  const linhas: Linha[] = alunos.map((a) => ({
    alunoId: a.id,
    nome: a.nome,
    detalhe: a.membro_id ? 'Membro' : 'Visitante',
  }))
  const conhecidos = new Set(linhas.map((l) => l.alunoId))
  for (const p of aula?.presencas ?? []) {
    if (!conhecidos.has(p.aluno_id)) linhas.push({ alunoId: p.aluno_id, nome: p.nome, detalhe: 'Já saiu da classe' })
  }
  return linhas
}

interface FormProps {
  classe: EbdClasse
  aula: EbdAulaDetalhe | null
  alunos: EbdAluno[]
}

function FormularioAula({ classe, aula, alunos }: FormProps) {
  const navegar = useNavigate()
  const linhas = montarLinhas(alunos, aula)
  const originais: Record<string, StatusPresenca> = Object.fromEntries(
    (aula?.presencas ?? []).map((p) => [p.aluno_id, p.status]),
  )
  const voltar = `/ebd/${classe.id}?aba=aulas`

  const [data, setData] = useState(aula?.data ?? hojeLocal())
  const [licao, setLicao] = useState(aula?.licao ?? '')
  const [marcas, setMarcas] = useState<Record<string, StatusPresenca>>(originais)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const lancados = linhas.filter((l) => marcas[l.alunoId]).length
  const resumo = STATUS.map((st) => ({ st, n: linhas.filter((l) => marcas[l.alunoId] === st).length }))

  function marcarTodosPresentes() {
    setMarcas((atuais) => {
      const novo = { ...atuais }
      for (const l of linhas) novo[l.alunoId] ??= 'P' // só quem ainda não tem marca
      return novo
    })
  }

  async function salvar(e: FormEvent) {
    e.preventDefault()
    if (!data) return setErro('Informe a data da aula.')
    if (data > hojeLocal()) return setErro('A data da aula não pode estar no futuro.')

    setErro(null)
    setEnviando(true)
    try {
      const licaoLimpa = licao.trim() || null
      if (aula === null) {
        const presencas: EbdItemPresenca[] = Object.entries(marcas).map(([aluno_id, status]) => ({ aluno_id, status }))
        const criada = await ebdApi.criarAula(classe.id, { data, licao: licaoLimpa, presencas })
        navegar(voltar, { replace: true, state: { aviso: `Aula de ${formatarData(criada.data)} registrada.` } })
        return
      }

      if (data !== aula.data || licaoLimpa !== aula.licao) {
        await ebdApi.atualizarAula(classe.id, aula.id, { data, licao: licaoLimpa })
      }
      // Só o que mudou em relação ao que já estava lançado
      const alteradas: EbdItemPresenca[] = Object.entries(marcas)
        .filter(([aluno_id, status]) => originais[aluno_id] !== status)
        .map(([aluno_id, status]) => ({ aluno_id, status }))
      if (alteradas.length > 0) await ebdApi.lancarPresencas(classe.id, aula.id, alteradas)

      navegar(voltar, { replace: true, state: { aviso: `Aula de ${formatarData(data)} atualizada.` } })
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar a aula.')
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={salvar} noValidate>
      <div className="grade">
        <Campo rotulo="Data *" type="date" max={hojeLocal()} value={data} onChange={(e) => setData(e.target.value)} required />
        <Campo rotulo="Lição" value={licao} onChange={(e) => setLicao(e.target.value)} maxLength={255} />
      </div>

      <div className="titulo-linha">
        <h2 className="subtitulo-h2">Presença</h2>
        <button type="button" className="botao secundario pequeno" onClick={marcarTodosPresentes} disabled={linhas.length === 0}>
          Marcar quem falta como presente
        </button>
      </div>

      {linhas.length === 0 ? (
        <p className="vazio-texto">
          Esta classe ainda não tem alunos. <Link to={`/ebd/${classe.id}`}>Cadastre os alunos</Link> para lançar presença.
        </p>
      ) : (
        <>
          <p className="ajuda" aria-live="polite">
            {lancados} de {linhas.length} lançados · {resumo.map((r) => `${STATUS_PRESENCA[r.st]}: ${r.n}`).join(' · ')}.
            Quem ficar sem marca não recebe lançamento.
          </p>
          <div className="tabela-wrap">
            <table>
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Presença</th>
                </tr>
              </thead>
              <tbody>
                {linhas.map((l) => (
                  <tr key={l.alunoId}>
                    <td>
                      {l.nome}
                      <br />
                      <small className="ajuda">{l.detalhe}</small>
                    </td>
                    <td>
                      <div role="radiogroup" aria-label={`Presença de ${l.nome}`} className="segmentado">
                        {STATUS.map((st) => (
                          <label key={st} className={marcas[l.alunoId] === st ? `seg ativo st-${st}` : 'seg'} title={STATUS_PRESENCA[st]}>
                            <input
                              type="radio"
                              name={`presenca-${l.alunoId}`}
                              value={st}
                              checked={marcas[l.alunoId] === st}
                              onChange={() => setMarcas((atuais) => ({ ...atuais, [l.alunoId]: st }))}
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
        <button type="submit" className="botao" disabled={enviando || !classe.ativa}>
          {enviando ? 'Salvando…' : aula === null ? 'Registrar aula' : 'Salvar alterações'}
        </button>
        <Link to={voltar} className="botao secundario">Cancelar</Link>
      </div>
    </form>
  )
}

export function EbdAulaPage() {
  const { id = '', aulaId } = useParams<{ id: string; aulaId: string }>()
  const classe = useCarga(() => ebdApi.obter(id), [id])
  const alunos = useCarga(() => ebdApi.alunos(id), [id])
  const aula = useCarga<EbdAulaDetalhe | null>(
    () => (aulaId ? ebdApi.aula(id, aulaId) : Promise.resolve(null)),
    [id, aulaId],
  )

  const erro = classe.erro ?? alunos.erro ?? aula.erro
  if (erro) {
    return (
      <section className="pagina">
        <p className="aviso erro" role="alert">{erro}</p>
        <Link to={`/ebd/${id}?aba=aulas`}>← Voltar</Link>
      </section>
    )
  }
  if (!classe.dados || !alunos.dados || aula.dados === undefined) return <Carregando />

  return (
    <section className="pagina estreita-media">
      <p className="migalha">
        <Link to={`/ebd/${id}?aba=aulas`}>← {classe.dados.nome}: aulas</Link>
      </p>
      <h1>{aulaId ? 'Aula' : 'Nova aula'}</h1>
      <FormularioAula key={aulaId ?? 'nova'} classe={classe.dados} alunos={alunos.dados} aula={aula.dados} />
    </section>
  )
}
