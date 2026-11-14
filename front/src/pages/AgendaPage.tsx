import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { AgendarTab } from '../components/AgendarTab'
import { AtendimentosLista } from '../components/AtendimentosLista'
import { DisponibilidadeTab } from '../components/DisponibilidadeTab'
import { RelatorioTab } from '../components/RelatorioTab'
import { ehOficial } from '../permissoes'

type AbaId = 'agendar' | 'meus' | 'recebidos' | 'disponibilidade' | 'relatorio'

/**
 * Conversas com pastor e presbíteros. Quem tem conta ligada a um membro pede horários;
 * pastor e presbíteros também respondem os pedidos e abrem a própria agenda.
 * O backend decide o que cada um vê: só o solicitante e o oficial enxergam um atendimento.
 */
export function AgendaPage() {
  const { usuario } = useAuth()
  const oficial = ehOficial(usuario)
  const podePedir = usuario?.membro_id != null
  const [params, setParams] = useSearchParams()

  const abas: { id: AbaId; rotulo: string }[] = [
    ...(podePedir
      ? [
          { id: 'agendar' as const, rotulo: 'Agendar conversa' },
          { id: 'meus' as const, rotulo: 'Meus pedidos' },
        ]
      : []),
    ...(oficial
      ? [
          { id: 'recebidos' as const, rotulo: 'Pedidos recebidos' },
          { id: 'disponibilidade' as const, rotulo: 'Meus horários' },
          { id: 'relatorio' as const, rotulo: 'Relatório' },
        ]
      : []),
  ]
  const aba = abas.find((a) => a.id === params.get('aba'))?.id ?? abas[0]?.id

  function ir(id: AbaId) {
    setParams({ aba: id }, { replace: true })
  }

  if (!aba) {
    return (
      <section className="pagina">
        <h1>Agenda de conversas</h1>
        <p className="vazio-texto">Sua conta não está ligada a um membro. Peça à secretaria para vinculá-la.</p>
      </section>
    )
  }

  return (
    <section className="pagina">
      <h1>Agenda de conversas</h1>
      <p className="subtitulo">Converse com o pastor ou com um presbítero. O assunto é sigiloso.</p>

      <div className="abas" role="tablist" aria-label="Seções da agenda">
        {abas.map((a) => (
          <button
            key={a.id}
            type="button"
            role="tab"
            id={`aba-${a.id}`}
            aria-selected={aba === a.id}
            aria-controls={`painel-${a.id}`}
            className={aba === a.id ? 'aba ativa' : 'aba'}
            onClick={() => ir(a.id)}
          >
            {a.rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="painel">
        {aba === 'agendar' && <AgendarTab onSolicitado={() => ir('meus')} />}
        {aba === 'meus' && <AtendimentosLista papel="solicitante" />}
        {aba === 'recebidos' && <AtendimentosLista papel="oficial" />}
        {aba === 'disponibilidade' && <DisponibilidadeTab />}
        {aba === 'relatorio' && <RelatorioTab />}
      </div>
    </section>
  )
}
