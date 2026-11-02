import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { comunicadosApi, sociedadesApi } from '../api/endpoints'
import type { CategoriaPost, Comunicado, NovoComunicado, Sociedade, TipoPublico } from '../api/types'
import { Campo } from '../components/Campo'
import { CampoSelect } from '../components/CampoSelect'
import { Carregando } from '../components/Carregando'
import { CATEGORIA, PUBLICO } from '../rotulos'
import { useAcessoSociedades } from '../useAcessoSociedades'
import { useCarga } from '../useCarga'

const MAX_CORPO = 10000

interface Props {
  comunicado: Comunicado | null
  sociedades: Sociedade[]
  gestor: boolean
}

function Formulario({ comunicado, sociedades, gestor }: Props) {
  const navegar = useNavigate()
  // Admin e pastor escrevem para qualquer público; a liderança, só para a própria sociedade
  const publicos = (gestor ? Object.keys(PUBLICO) : ['sociedade']) as TipoPublico[]

  const [titulo, setTitulo] = useState(comunicado?.titulo ?? '')
  const [corpo, setCorpo] = useState(comunicado?.corpo ?? '')
  const [categoria, setCategoria] = useState<CategoriaPost>(comunicado?.categoria ?? 'aviso')
  const [publico, setPublico] = useState<TipoPublico>(comunicado?.publico ?? publicos[0])
  const [sociedadeId, setSociedadeId] = useState(comunicado?.sociedade_id ?? (sociedades.length === 1 ? sociedades[0].id : ''))
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function salvar(e: FormEvent, publicarAgora = false) {
    e.preventDefault()
    if (!titulo.trim()) return setErro('Informe o título.')
    if (!corpo.trim()) return setErro('Escreva o texto do comunicado.')
    if (publico === 'sociedade' && !sociedadeId) return setErro('Escolha a sociedade.')

    const dados: NovoComunicado = {
      titulo: titulo.trim(),
      corpo: corpo.trim(),
      categoria,
      publico,
      sociedade_id: publico === 'sociedade' ? sociedadeId : null,
    }
    setErro(null)
    setEnviando(true)
    try {
      let aviso: string
      if (comunicado) {
        await comunicadosApi.atualizar(comunicado.id, dados)
        aviso = `"${dados.titulo}" atualizado.`
      } else {
        const criado = await comunicadosApi.criar(dados)
        if (publicarAgora) {
          await comunicadosApi.publicar(criado.id)
          aviso = `"${dados.titulo}" publicado.`
        } else {
          aviso = `Rascunho "${dados.titulo}" salvo. Publique quando estiver pronto.`
        }
      }
      navegar('/comunicados/gerenciar', { replace: true, state: { aviso } })
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar o comunicado.')
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={(e) => salvar(e)} noValidate>
      {comunicado?.status === 'publicado' && (
        <p className="aviso atencao" role="status">
          Este comunicado já está publicado: as alterações aparecem no mural assim que você salvar.
        </p>
      )}
      <Campo rotulo="Título *" value={titulo} onChange={(e) => setTitulo(e.target.value)} maxLength={200} required autoFocus />
      <div className="grade">
        <CampoSelect rotulo="Categoria" value={categoria} onChange={(e) => setCategoria(e.target.value as CategoriaPost)}>
          {Object.entries(CATEGORIA).map(([v, r]) => (
            <option key={v} value={v}>{r}</option>
          ))}
        </CampoSelect>
        <CampoSelect
          rotulo="Quem vai ler"
          value={publico}
          onChange={(e) => setPublico(e.target.value as TipoPublico)}
          disabled={publicos.length === 1}
          ajuda={publico === 'professores_ebd' ? 'Por enquanto só administrador e pastor veem este público.' : undefined}
        >
          {publicos.map((v) => (
            <option key={v} value={v}>{PUBLICO[v]}</option>
          ))}
        </CampoSelect>
      </div>
      {publico === 'sociedade' && (
        <CampoSelect rotulo="Sociedade" value={sociedadeId} onChange={(e) => setSociedadeId(e.target.value)}>
          <option value="">Selecione…</option>
          {sociedades.map((s) => (
            <option key={s.id} value={s.id}>{s.sigla}{s.nome ? ` — ${s.nome}` : ''}</option>
          ))}
        </CampoSelect>
      )}
      <div className="campo">
        <label htmlFor="c-corpo">Texto *</label>
        <textarea id="c-corpo" rows={10} value={corpo} onChange={(e) => setCorpo(e.target.value)} maxLength={MAX_CORPO} />
        <small className="ajuda">{corpo.length} de {MAX_CORPO} caracteres. As quebras de linha são mantidas.</small>
      </div>

      {erro && <p className="aviso erro" role="alert">{erro}</p>}
      <div className="acoes-form">
        <button type="submit" className="botao" disabled={enviando}>
          {enviando ? 'Salvando…' : comunicado ? 'Salvar alterações' : 'Salvar rascunho'}
        </button>
        {!comunicado && (
          <button type="button" className="botao secundario" disabled={enviando} onClick={(e) => salvar(e, true)}>
            Salvar e publicar agora
          </button>
        )}
        <Link to="/comunicados/gerenciar" className="botao secundario">Cancelar</Link>
      </div>
    </form>
  )
}

export function ComunicadoFormPage() {
  const { id } = useParams<{ id: string }>()
  const { gestor } = useAcessoSociedades()
  const comunicado = useCarga<Comunicado | null>(() => (id ? comunicadosApi.obter(id) : Promise.resolve(null)), [id])
  // Para o gestor, todas as sociedades; para a liderança, a API já devolve só a dela
  const sociedades = useCarga(() => sociedadesApi.listar().catch(() => [] as Sociedade[]), [])

  const erro = comunicado.erro ?? sociedades.erro
  if (erro) {
    return (
      <section className="pagina estreita-media">
        <p className="aviso erro" role="alert">{erro}</p>
        <Link to="/comunicados/gerenciar">← Voltar</Link>
      </section>
    )
  }
  if (comunicado.dados === undefined || !sociedades.dados) return <Carregando />

  return (
    <section className="pagina estreita-media">
      <p className="migalha">
        <Link to="/comunicados/gerenciar">← Gerenciar comunicados</Link>
      </p>
      <h1>{id ? 'Editar comunicado' : 'Novo comunicado'}</h1>
      <Formulario key={id ?? 'novo'} comunicado={comunicado.dados} sociedades={sociedades.dados} gestor={gestor} />
    </section>
  )
}
