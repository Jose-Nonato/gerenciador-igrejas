import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { agendaApi } from '../api/endpoints'
import type { Disponibilidade, ModalidadeAtendimento } from '../api/types'
import { DIA_SEMANA, MODALIDADE } from '../rotulos'
import { useCarga } from '../useCarga'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'
import { Carregando } from './Carregando'
import { BloqueiosSecao } from './BloqueiosSecao'
import { Dialogo } from './Dialogo'
import { DialogoConfirmar } from './DialogoConfirmar'

const DURACOES = [15, 20, 30, 45, 60, 90]
const hm = (t: string) => t.slice(0, 5)

function NovaJanelaDialogo({ onCriada, onFechar }: { onCriada: () => void; onFechar: () => void }) {
  const [diaSemana, setDiaSemana] = useState(1)
  const [inicio, setInicio] = useState('19:00')
  const [fim, setFim] = useState('21:00')
  const [duracao, setDuracao] = useState(30)
  const [modalidade, setModalidade] = useState<ModalidadeAtendimento>('presencial')
  const [local, setLocal] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!inicio || !fim) return setErro('Informe o início e o fim.')
    if (fim <= inicio) return setErro('O fim deve ser depois do início.')
    setErro(null)
    setEnviando(true)
    try {
      await agendaApi.criarDisponibilidade({
        dia_semana: diaSemana,
        hora_inicio: inicio,
        hora_fim: fim,
        duracao_min: duracao,
        modalidade,
        local: local.trim() || null,
      })
      onCriada()
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar a janela.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Nova janela de atendimento" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <CampoSelect rotulo="Dia da semana" value={diaSemana} onChange={(e) => setDiaSemana(Number(e.target.value))}>
          {DIA_SEMANA.map((nome, i) => (
            <option key={nome} value={i}>
              {nome}
            </option>
          ))}
        </CampoSelect>
        <Campo rotulo="Início" type="time" value={inicio} onChange={(e) => setInicio(e.target.value)} />
        <Campo rotulo="Fim" type="time" value={fim} onChange={(e) => setFim(e.target.value)} />
        <CampoSelect
          rotulo="Duração de cada conversa"
          value={duracao}
          onChange={(e) => setDuracao(Number(e.target.value))}
          ajuda="A janela é dividida em horários desta duração."
        >
          {DURACOES.map((d) => (
            <option key={d} value={d}>
              {d} minutos
            </option>
          ))}
        </CampoSelect>
        <CampoSelect rotulo="Modalidade" value={modalidade} onChange={(e) => setModalidade(e.target.value as ModalidadeAtendimento)}>
          {(Object.keys(MODALIDADE) as ModalidadeAtendimento[]).map((m) => (
            <option key={m} value={m}>
              {MODALIDADE[m]}
            </option>
          ))}
        </CampoSelect>
        <Campo
          rotulo="Local ou link (opcional)"
          value={local}
          onChange={(e) => setLocal(e.target.value)}
          maxLength={255}
          ajuda="Ex.: gabinete pastoral, ou o link da chamada."
        />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Salvar janela'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}

export function DisponibilidadeTab() {
  const { dados, erro, carregando, recarregar } = useCarga(() => agendaApi.disponibilidades(), [])
  const [criando, setCriando] = useState(false)
  const [removendo, setRemovendo] = useState<Disponibilidade | null>(null)
  const [erroAcao, setErroAcao] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)

  async function alternar(d: Disponibilidade) {
    setErroAcao(null)
    try {
      await agendaApi.atualizarDisponibilidade(d.id, { ativa: !d.ativa })
      recarregar()
    } catch (err) {
      setErroAcao(err instanceof ApiError ? err.message : 'Não foi possível alterar a janela.')
    }
  }

  async function remover() {
    if (!removendo) return
    setOcupado(true)
    setErroAcao(null)
    try {
      await agendaApi.removerDisponibilidade(removendo.id)
      setRemovendo(null)
      recarregar()
    } catch (err) {
      setErroAcao(err instanceof ApiError ? err.message : 'Não foi possível remover a janela.')
    } finally {
      setOcupado(false)
    }
  }

  if (erro && !dados) return <p className="aviso erro" role="alert">{erro}</p>
  if (!dados) return <Carregando />

  return (
    <div>
      <div className="titulo-linha">
        <p className="subtitulo">Os membros só conseguem pedir conversa nos horários das janelas ativas.</p>
        <button type="button" className="botao" onClick={() => setCriando(true)}>
          Nova janela
        </button>
      </div>
      {erroAcao && <p className="aviso erro" role="alert">{erroAcao}</p>}

      {dados.length === 0 ? (
        <p className="vazio-texto">Você ainda não abriu nenhum horário de atendimento.</p>
      ) : (
        <div className="tabela-wrap" aria-busy={carregando}>
          <table>
            <thead>
              <tr>
                <th>Dia</th>
                <th>Horário</th>
                <th>Duração</th>
                <th>Onde</th>
                <th>Situação</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {dados.map((d) => (
                <tr key={d.id}>
                  <td>{DIA_SEMANA[d.dia_semana]}</td>
                  <td>
                    {hm(d.hora_inicio)} às {hm(d.hora_fim)}
                  </td>
                  <td>{d.duracao_min} min</td>
                  <td>
                    {MODALIDADE[d.modalidade]}
                    {d.local ? ` · ${d.local}` : ''}
                  </td>
                  <td>{d.ativa ? <span className="selo ativo">Ativa</span> : <span className="selo">Pausada</span>}</td>
                  <td className="acoes">
                    <button type="button" className="botao secundario" onClick={() => alternar(d)}>
                      {d.ativa ? 'Pausar' : 'Reativar'}
                    </button>
                    <button type="button" className="botao secundario" onClick={() => setRemovendo(d)}>
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <hr />
      <BloqueiosSecao />

      {criando && (
        <NovaJanelaDialogo
          onFechar={() => setCriando(false)}
          onCriada={() => {
            setCriando(false)
            recarregar()
          }}
        />
      )}

      <DialogoConfirmar
        aberto={removendo !== null}
        titulo="Remover janela"
        rotuloConfirmar="Remover"
        rotuloOcupado="Removendo…"
        ocupado={ocupado}
        erro={erroAcao}
        onConfirmar={remover}
        onCancelar={() => setRemovendo(null)}
      >
        <p>
          Remover a janela de {removendo ? DIA_SEMANA[removendo.dia_semana].toLowerCase() : ''}? As conversas já marcadas
          continuam valendo.
        </p>
      </DialogoConfirmar>
    </div>
  )
}
