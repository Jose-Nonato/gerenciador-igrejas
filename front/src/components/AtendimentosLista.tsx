import { useState } from 'react'
import { ApiError } from '../api/client'
import { agendaApi } from '../api/endpoints'
import type { Atendimento, StatusAtendimento } from '../api/types'
import { formatarDataHora } from '../formatar'
import { CATEGORIA_ATENDIMENTO, MODALIDADE, STATUS_ATENDIMENTO } from '../rotulos'
import { useCarga } from '../useCarga'
import { Carregando } from './Carregando'
import { JustificativaDialogo } from './JustificativaDialogo'
import { RemarcarDialogo } from './RemarcarDialogo'

interface Props {
  /** `solicitante`: os pedidos que eu fiz. `oficial`: os que recebi como pastor ou presbítero. */
  papel: 'solicitante' | 'oficial'
}

type Pendente = { tipo: 'recusar' | 'cancelar'; atendimento: Atendimento }

export function AtendimentosLista({ papel }: Props) {
  const oficial = papel === 'oficial'
  const [filtro, setFiltro] = useState<StatusAtendimento | ''>('')
  // O "agora" é tirado na hora da consulta (não no render): decide se o horário já passou
  const { dados: carga, erro, carregando, recarregar } = useCarga(async () => {
    const lista = await (oficial ? agendaApi.recebidos(filtro || undefined) : agendaApi.meus(filtro || undefined))
    return { lista, agora: Date.now() }
  }, [papel, filtro])
  const dados = carga?.lista
  const agora = carga?.agora ?? 0
  const [erroAcao, setErroAcao] = useState<string | null>(null)
  const [pendente, setPendente] = useState<Pendente | null>(null)
  const [remarcando, setRemarcando] = useState<Atendimento | null>(null)

  async function agir(acao: () => Promise<unknown>) {
    setErroAcao(null)
    try {
      await acao()
      recarregar()
    } catch (err) {
      setErroAcao(err instanceof ApiError ? err.message : 'Não foi possível concluir a ação.')
    }
  }

  if (erro && !dados) return <p className="aviso erro" role="alert">{erro}</p>
  if (!dados) return <Carregando />

  return (
    <div>
      <div className="filtros">
        <div className="campo filtro-unico">
          <label htmlFor="f-status">Situação</label>
          <select id="f-status" value={filtro} onChange={(e) => setFiltro(e.target.value as StatusAtendimento | '')}>
            <option value="">Todas</option>
            {(Object.keys(STATUS_ATENDIMENTO) as StatusAtendimento[]).map((s) => (
              <option key={s} value={s}>
                {STATUS_ATENDIMENTO[s]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {erroAcao && <p className="aviso erro" role="alert">{erroAcao}</p>}

      {dados.length === 0 ? (
        <p className="vazio-texto">
          {oficial ? 'Nenhum pedido de conversa recebido.' : 'Você ainda não pediu nenhuma conversa.'}
        </p>
      ) : (
        <div className="tabela-wrap" aria-busy={carregando}>
          <table>
            <thead>
              <tr>
                <th>Quando</th>
                <th>{oficial ? 'Membro' : 'Com'}</th>
                <th>Onde</th>
                <th>Assunto</th>
                <th>Situação</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {dados.map((a) => {
                const jaPassou = new Date(a.inicio).getTime() <= agora
                return (
                  <tr key={a.id}>
                    <td>{formatarDataHora(a.inicio)}</td>
                    <td>{oficial ? a.solicitante_nome : a.oficial_nome}</td>
                    <td>
                      {MODALIDADE[a.modalidade]}
                      {a.local ? ` · ${a.local}` : ''}
                    </td>
                    <td>
                      {CATEGORIA_ATENDIMENTO[a.categoria]}
                      {a.assunto && (
                        <>
                          <br />
                          <small className="ajuda" style={{ whiteSpace: 'normal' }}>{a.assunto}</small>
                        </>
                      )}
                    </td>
                    <td>
                      <span className={`selo status-atendimento-${a.status}`}>{STATUS_ATENDIMENTO[a.status]}</span>
                      {a.status === 'remarcacao' && a.proposta_inicio && (
                        <>
                          <br />
                          <small className="ajuda" style={{ whiteSpace: 'normal' }}>
                            Proposto: {formatarDataHora(a.proposta_inicio)}
                            {a.proposta_modalidade ? ` · ${MODALIDADE[a.proposta_modalidade]}` : ''}
                            {a.proposta_local ? ` · ${a.proposta_local}` : ''}
                          </small>
                        </>
                      )}
                      {a.justificativa && (
                        <>
                          <br />
                          <small className="ajuda" style={{ whiteSpace: 'normal' }}>{a.justificativa}</small>
                        </>
                      )}
                    </td>
                    <td className="acoes">
                      {oficial && a.status === 'solicitado' && (
                        <>
                          <button type="button" className="botao" onClick={() => agir(() => agendaApi.confirmar(a.id))}>
                            Confirmar
                          </button>
                          <button
                            type="button"
                            className="botao secundario"
                            onClick={() => setPendente({ tipo: 'recusar', atendimento: a })}
                          >
                            Recusar
                          </button>
                        </>
                      )}
                      {oficial && a.status === 'confirmado' && jaPassou && (
                        <>
                          <button type="button" className="botao" onClick={() => agir(() => agendaApi.concluir(a.id))}>
                            Realizado
                          </button>
                          <button
                            type="button"
                            className="botao secundario"
                            onClick={() => agir(() => agendaApi.faltou(a.id))}
                          >
                            Não compareceu
                          </button>
                        </>
                      )}
                      {oficial && (a.status === 'solicitado' || a.status === 'confirmado') && !jaPassou && (
                        <button type="button" className="botao secundario" onClick={() => setRemarcando(a)}>
                          Remarcar
                        </button>
                      )}
                      {!oficial && a.status === 'remarcacao' && (
                        <button type="button" className="botao" onClick={() => agir(() => agendaApi.aceitarRemarcacao(a.id))}>
                          Aceitar novo horário
                        </button>
                      )}
                      {((!oficial && a.status === 'solicitado') ||
                        (a.status === 'confirmado' && !jaPassou) ||
                        a.status === 'remarcacao') && (
                        <button
                          type="button"
                          className="botao secundario"
                          onClick={() => setPendente({ tipo: 'cancelar', atendimento: a })}
                        >
                          {a.status !== 'remarcacao' ? 'Cancelar' : oficial ? 'Retirar proposta' : 'Recusar novo horário'}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {pendente && (
        <JustificativaDialogo
          titulo={pendente.tipo === 'recusar' ? 'Recusar pedido' : 'Cancelar conversa'}
          texto={
            pendente.tipo === 'recusar'
              ? `Recusar o pedido de ${pendente.atendimento.solicitante_nome} em ${formatarDataHora(pendente.atendimento.inicio)}?`
              : pendente.atendimento.status === 'remarcacao'
                ? oficial
                  ? 'Retirar a proposta de novo horário? A conversa será cancelada.'
                  : 'Recusar o novo horário cancela esta conversa. Deseja continuar?'
                : `Cancelar a conversa de ${formatarDataHora(pendente.atendimento.inicio)}? O horário volta a ficar livre.`
          }
          rotuloConfirmar={pendente.tipo === 'recusar' ? 'Recusar pedido' : 'Cancelar conversa'}
          onFechar={() => setPendente(null)}
          onConfirmar={async (motivo) => {
            const { tipo, atendimento } = pendente
            if (tipo === 'recusar') await agendaApi.recusar(atendimento.id, motivo)
            else await agendaApi.cancelar(atendimento.id, motivo)
            setPendente(null)
            recarregar()
          }}
        />
      )}

      {remarcando && (
        <RemarcarDialogo
          atendimento={remarcando}
          onFechar={() => setRemarcando(null)}
          onRemarcado={() => {
            setRemarcando(null)
            recarregar()
          }}
        />
      )}
    </div>
  )
}
