import { useState } from 'react'
import { ApiError } from '../api/client'
import { agendaOficialApi } from '../api/endpoints'
import type { Atendimento, Horario } from '../api/types'
import { diaPorExtenso, formatarDataHora, hojeLocal, horaCurta, somarDias } from '../formatar'
import { MODALIDADE } from '../rotulos'
import { useCarga } from '../useCarga'
import { Carregando } from './Carregando'
import { Dialogo } from './Dialogo'
import { HorariosPorDia } from './HorariosPorDia'

const DIAS_A_FRENTE = 30

interface Props {
  atendimento: Atendimento
  onRemarcado: () => void
  onFechar: () => void
}

/** O oficial escolhe, na própria agenda, outro horário para a conversa e o propõe. */
export function RemarcarDialogo({ atendimento, onRemarcado, onFechar }: Props) {
  const hoje = hojeLocal()
  const { dados: horarios, erro: erroCarga } = useCarga(
    () => agendaOficialApi.meusHorarios(hoje, somarDias(hoje, DIAS_A_FRENTE)),
    [hoje],
  )
  const [escolhido, setEscolhido] = useState<Horario | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function propor() {
    if (!escolhido) return
    setErro(null)
    setEnviando(true)
    try {
      await agendaOficialApi.remarcar(atendimento.id, escolhido.inicio)
      onRemarcado()
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível propor o novo horário.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Propor outro horário" onFechar={onFechar}>
      <p>
        Conversa com <strong>{atendimento.solicitante_nome}</strong>, hoje marcada para{' '}
        {formatarDataHora(atendimento.inicio)}. {atendimento.solicitante_nome} precisa aceitar o novo horário.
      </p>
      {erroCarga && !horarios ? (
        <p className="aviso erro" role="alert">{erroCarga}</p>
      ) : !horarios ? (
        <Carregando />
      ) : horarios.length === 0 ? (
        <p className="vazio-texto">
          Você não tem horários livres nos próximos {DIAS_A_FRENTE} dias. Abra mais janelas em &quot;Meus horários&quot;.
        </p>
      ) : (
        <HorariosPorDia horarios={horarios} escolhido={escolhido?.inicio} onEscolher={setEscolhido} />
      )}
      {escolhido && (
        <p>
          Novo horário: <strong>{diaPorExtenso(escolhido.inicio)}, {horaCurta(escolhido.inicio)}</strong> ·{' '}
          {MODALIDADE[escolhido.modalidade]}
          {escolhido.local ? ` (${escolhido.local})` : ''}
        </p>
      )}
      {erro && <p className="aviso erro" role="alert">{erro}</p>}
      <div className="acoes-form">
        <button type="button" className="botao" onClick={propor} disabled={!escolhido || enviando}>
          {enviando ? 'Enviando…' : 'Propor este horário'}
        </button>
        <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
          Cancelar
        </button>
      </div>
    </Dialogo>
  )
}
