import { Link, useParams, useSearchParams } from 'react-router-dom'
import { sociedadesApi } from '../api/endpoints'
import { Carregando } from '../components/Carregando'
import { FrequenciaTab } from '../components/FrequenciaTab'
import { ReunioesTab } from '../components/ReunioesTab'
import { SociosTab } from '../components/SociosTab'
import { SIGLA } from '../rotulos'
import { useCarga } from '../useCarga'

const ABAS = [
  { id: 'socios', rotulo: 'Sócios' },
  { id: 'reunioes', rotulo: 'Reuniões' },
  { id: 'frequencia', rotulo: 'Frequência' },
] as const

type AbaId = (typeof ABAS)[number]['id']

export function SociedadePage() {
  const { id = '' } = useParams<{ id: string }>()
  const [params, setParams] = useSearchParams()
  // A aba vai na URL: voltar de uma reunião cai de novo em "Reuniões"
  const aba: AbaId = ABAS.find((a) => a.id === params.get('aba'))?.id ?? 'socios'
  const { dados: sociedade, erro, recarregar } = useCarga(() => sociedadesApi.obter(id), [id])

  if (erro && !sociedade) {
    return (
      <section className="pagina">
        <p className="aviso erro" role="alert">{erro}</p>
        <Link to="/sociedades">← Sociedades</Link>
      </section>
    )
  }
  if (!sociedade) return <Carregando />

  return (
    <section className="pagina">
      <p className="migalha">
        <Link to="/sociedades">← Sociedades</Link>
      </p>
      <h1>{sociedade.sigla}{sociedade.nome ? ` — ${sociedade.nome}` : ''}</h1>
      <p className="subtitulo">
        {SIGLA[sociedade.sigla]} · {sociedade.total_socios} {sociedade.total_socios === 1 ? 'sócio' : 'sócios'}
      </p>

      <div className="abas" role="tablist" aria-label="Seções da sociedade">
        {ABAS.map((a) => (
          <button
            key={a.id}
            type="button"
            role="tab"
            id={`aba-${a.id}`}
            aria-selected={aba === a.id}
            aria-controls={`painel-${a.id}`}
            className={aba === a.id ? 'aba ativa' : 'aba'}
            onClick={() => setParams({ aba: a.id }, { replace: true })}
          >
            {a.rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="painel">
        {aba === 'socios' && <SociosTab sociedadeId={id} onMudou={recarregar} />}
        {aba === 'reunioes' && <ReunioesTab sociedadeId={id} />}
        {aba === 'frequencia' && <FrequenciaTab sociedadeId={id} />}
      </div>
    </section>
  )
}
