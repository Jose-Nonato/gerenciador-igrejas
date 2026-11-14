import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { agendaApi } from '../api/endpoints'
import type { CategoriaAtendimento, Horario } from '../api/types'
import { diaPorExtenso, hojeLocal, horaCurta, somarDias } from '../formatar'
import { CATEGORIA_ATENDIMENTO, MODALIDADE, PERFIL } from '../rotulos'
import { useCarga } from '../useCarga'
import { CampoSelect } from './CampoSelect'
import { Carregando } from './Carregando'
import { Dialogo } from './Dialogo'
import { HorariosPorDia } from './HorariosPorDia'

const DIAS_A_FRENTE = 30
const MAX_ASSUNTO = 2000

function PedidoDialogo({
  oficialId,
  oficialNome,
  horario,
  onFeito,
  onFechar,
}: {
  oficialId: string
  oficialNome: string
  horario: Horario
  onFeito: () => void
  onFechar: () => void
}) {
  const [categoria, setCategoria] = useState<CategoriaAtendimento>('aconselhamento')
  const [assunto, setAssunto] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await agendaApi.solicitar({
        oficial_id: oficialId,
        inicio: horario.inicio,
        categoria,
        assunto: assunto.trim() || null,
      })
      onFeito()
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível enviar o pedido.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Pedir conversa" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <p>
          <strong>{oficialNome}</strong> · {diaPorExtenso(horario.inicio)}, {horaCurta(horario.inicio)} às {horaCurta(horario.fim)} ·{' '}
          {MODALIDADE[horario.modalidade]}
          {horario.local ? ` (${horario.local})` : ''}
        </p>
        <CampoSelect rotulo="Tipo de conversa" value={categoria} onChange={(e) => setCategoria(e.target.value as CategoriaAtendimento)}>
          {(Object.keys(CATEGORIA_ATENDIMENTO) as CategoriaAtendimento[]).map((c) => (
            <option key={c} value={c}>
              {CATEGORIA_ATENDIMENTO[c]}
            </option>
          ))}
        </CampoSelect>
        <div className="campo">
          <label htmlFor="p-assunto">Assunto (opcional)</label>
          <textarea id="p-assunto" rows={4} value={assunto} onChange={(e) => setAssunto(e.target.value)} maxLength={MAX_ASSUNTO} />
          <small className="ajuda">
            Só você e {oficialNome} veem o que escrever aqui. {assunto.length} de {MAX_ASSUNTO} caracteres.
          </small>
        </div>
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Enviando…' : 'Enviar pedido'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}

export function AgendarTab({ onSolicitado }: { onSolicitado: () => void }) {
  const { dados: oficiais, erro: erroOficiais } = useCarga(() => agendaApi.oficiais(), [])
  const [oficialId, setOficialId] = useState('')
  const hoje = hojeLocal()
  const { dados: horarios, erro: erroHorarios, carregando, recarregar } = useCarga(
    () => (oficialId ? agendaApi.horarios(oficialId, hoje, somarDias(hoje, DIAS_A_FRENTE)) : Promise.resolve([])),
    [oficialId, hoje],
  )
  const [escolhido, setEscolhido] = useState<Horario | null>(null)

  if (erroOficiais && !oficiais) return <p className="aviso erro" role="alert">{erroOficiais}</p>
  if (!oficiais) return <Carregando />

  if (oficiais.length === 0) {
    return <p className="vazio-texto">Nenhum pastor ou presbítero abriu horários de atendimento ainda.</p>
  }

  const oficial = oficiais.find((o) => o.id === oficialId)

  return (
    <div>
      <CampoSelect rotulo="Com quem você quer conversar?" value={oficialId} onChange={(e) => setOficialId(e.target.value)}>
        <option value="">Escolha…</option>
        {oficiais.map((o) => (
          <option key={o.id} value={o.id}>
            {o.nome} ({PERFIL[o.perfil]})
          </option>
        ))}
      </CampoSelect>

      {oficial && (
        <>
          {erroHorarios && <p className="aviso erro" role="alert">{erroHorarios}</p>}
          {carregando ? (
            <Carregando />
          ) : (horarios ?? []).length === 0 ? (
            <p className="vazio-texto">
              Nenhum horário livre nos próximos {DIAS_A_FRENTE} dias. Os pedidos precisam de pelo menos 24 horas de antecedência.
            </p>
          ) : (
            <HorariosPorDia horarios={horarios ?? []} onEscolher={setEscolhido} />
          )}
        </>
      )}

      {oficial && escolhido && (
        <PedidoDialogo
          oficialId={oficial.id}
          oficialNome={oficial.nome}
          horario={escolhido}
          onFechar={() => setEscolhido(null)}
          onFeito={() => {
            setEscolhido(null)
            recarregar()
            onSolicitado()
          }}
        />
      )}
    </div>
  )
}
