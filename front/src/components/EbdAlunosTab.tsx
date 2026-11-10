import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { ebdApi } from '../api/endpoints'
import type { EbdAluno } from '../api/types'
import { formatarData } from '../formatar'
import { useCarga } from '../useCarga'
import { Campo } from './Campo'
import { Carregando } from './Carregando'
import { Dialogo } from './Dialogo'
import { DialogoConfirmar } from './DialogoConfirmar'
import { SeletorMembro } from './SeletorMembro'

interface Props {
  classeId: string
  /** Classe desativada não recebe alterações */
  ativa: boolean
  /** Avisa a página quando o total de alunos mudou (o cabeçalho mostra a contagem) */
  onMudou: () => void
}

function AdicionarAlunoDialogo({
  classeId,
  onAdicionado,
  onFechar,
}: {
  classeId: string
  onAdicionado: (aluno: EbdAluno) => void
  onFechar: () => void
}) {
  const [visitante, setVisitante] = useState(false)
  const [membroId, setMembroId] = useState<string | null>(null)
  const [nomeMembro, setNomeMembro] = useState<string | null>(null)
  const [nomeExterno, setNomeExterno] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (visitante && !nomeExterno.trim()) return setErro('Informe o nome do visitante.')
    if (!visitante && !membroId) return setErro('Escolha o membro na busca.')
    setErro(null)
    setEnviando(true)
    try {
      onAdicionado(
        await ebdApi.adicionarAluno(
          classeId,
          visitante ? { nome_externo: nomeExterno.trim() } : { membro_id: membroId },
        ),
      )
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível adicionar o aluno.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Adicionar aluno" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <label className="marcador">
          <input type="checkbox" checked={visitante} onChange={(e) => setVisitante(e.target.checked)} />
          É visitante (não é membro da igreja)
        </label>

        {visitante ? (
          <Campo rotulo="Nome *" value={nomeExterno} onChange={(e) => setNomeExterno(e.target.value)} maxLength={255} autoFocus />
        ) : (
          <SeletorMembro
            rotulo="Membro"
            // Busca restrita: o professor pode não ter acesso ao rol
            buscar={(q) => ebdApi.buscarMembros(classeId, q)}
            nomeSelecionado={membroId ? nomeMembro : null}
            onSelecionar={(m) => {
              setMembroId(m?.id ?? null)
              setNomeMembro(m?.nome ?? null)
            }}
          />
        )}

        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Adicionando…' : 'Adicionar aluno'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}

export function EbdAlunosTab({ classeId, ativa, onMudou }: Props) {
  const [incluirEx, setIncluirEx] = useState(false)
  const { dados: alunos, erro, carregando, recarregar } = useCarga(
    () => ebdApi.alunos(classeId, incluirEx),
    [classeId, incluirEx],
  )
  const [aviso, setAviso] = useState<string | null>(null)
  const [adicionando, setAdicionando] = useState(false)
  const [removendo, setRemovendo] = useState<EbdAluno | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [erroRemocao, setErroRemocao] = useState<string | null>(null)

  async function remover() {
    if (!removendo) return
    setOcupado(true)
    setErroRemocao(null)
    try {
      await ebdApi.removerAluno(classeId, removendo.id)
      setAviso(`${removendo.nome} saiu da classe.`)
      setRemovendo(null)
      recarregar()
      onMudou()
    } catch (err) {
      setErroRemocao(err instanceof ApiError ? err.message : 'Não foi possível remover o aluno.')
    } finally {
      setOcupado(false)
    }
  }

  if (erro && !alunos) return <p className="aviso erro" role="alert">{erro}</p>
  if (!alunos) return <Carregando />

  return (
    <div>
      <div className="titulo-linha">
        <label className="marcador">
          <input type="checkbox" checked={incluirEx} onChange={(e) => setIncluirEx(e.target.checked)} />
          Mostrar quem já saiu
        </label>
        <button
          type="button"
          className="botao"
          disabled={!ativa}
          onClick={() => {
            setAviso(null)
            setAdicionando(true)
          }}
        >
          Adicionar aluno
        </button>
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}
      {erro && <p className="aviso erro" role="alert">{erro}</p>}

      <div className="tabela-wrap" aria-busy={carregando}>
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Vínculo</th>
              <th>Entrou em</th>
              <th>Situação</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {alunos.map((a) => (
              <tr key={a.id}>
                <td>{a.nome}</td>
                <td>{a.membro_id ? 'Membro' : 'Visitante'}</td>
                <td>{formatarData(a.entrou_em)}</td>
                <td>
                  {a.saiu_em ? (
                    <span className="selo">Saiu em {formatarData(a.saiu_em)}</span>
                  ) : (
                    <span className="selo ativo">Ativo</span>
                  )}
                </td>
                <td className="acoes">
                  {!a.saiu_em && ativa && (
                    <button
                      type="button"
                      className="botao secundario pequeno"
                      aria-label={`Remover ${a.nome}`}
                      onClick={() => setRemovendo(a)}
                    >
                      Remover
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {alunos.length === 0 && (
              <tr>
                <td colSpan={5} className="vazio">Nenhum aluno.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {adicionando && (
        <AdicionarAlunoDialogo
          classeId={classeId}
          onFechar={() => setAdicionando(false)}
          onAdicionado={(novo) => {
            setAdicionando(false)
            setAviso(`${novo.nome} foi adicionado(a) à classe.`)
            recarregar()
            onMudou()
          }}
        />
      )}

      <DialogoConfirmar
        aberto={removendo !== null}
        titulo="Remover da classe?"
        rotuloConfirmar="Remover aluno"
        rotuloOcupado="Removendo…"
        ocupado={ocupado}
        erro={erroRemocao}
        onConfirmar={remover}
        onCancelar={() => {
          setRemovendo(null)
          setErroRemocao(null)
        }}
      >
        <p>
          <strong>{removendo?.nome}</strong> deixa de ser aluno(a) desta classe, mas o histórico de presença é mantido.
          Se voltar, basta adicionar de novo.
        </p>
      </DialogoConfirmar>
    </div>
  )
}
