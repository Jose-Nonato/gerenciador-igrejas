import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { ebdApi } from '../api/endpoints'
import type { EbdProfessor } from '../api/types'
import { formatarData, hojeLocal } from '../formatar'
import { useCarga } from '../useCarga'
import { Carregando } from './Carregando'
import { Dialogo } from './Dialogo'
import { DialogoConfirmar } from './DialogoConfirmar'
import { SeletorMembro } from './SeletorMembro'

interface Props {
  classeId: string
  ativa: boolean
  /** Só admin e pastor definem os professores */
  gestor: boolean
  onMudou: () => void
}

function AdicionarProfessorDialogo({
  classeId,
  onAdicionado,
  onFechar,
}: {
  classeId: string
  onAdicionado: (professor: EbdProfessor) => void
  onFechar: () => void
}) {
  const [membroId, setMembroId] = useState<string | null>(null)
  const [nomeMembro, setNomeMembro] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!membroId) return setErro('Escolha o membro na busca.')
    setErro(null)
    setEnviando(true)
    try {
      onAdicionado(await ebdApi.adicionarProfessor(classeId, membroId))
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível adicionar o professor.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Adicionar professor" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <SeletorMembro
          rotulo="Membro"
          buscar={(q) => ebdApi.buscarMembros(classeId, q)}
          nomeSelecionado={membroId ? nomeMembro : null}
          onSelecionar={(m) => {
            setMembroId(m?.id ?? null)
            setNomeMembro(m?.nome ?? null)
          }}
        />
        <p className="ajuda">
          O professor passa a ver e cuidar desta classe quando o cadastro dele estiver vinculado a um usuário do sistema.
        </p>
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Adicionando…' : 'Adicionar professor'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}

export function EbdProfessoresTab({ classeId, ativa, gestor, onMudou }: Props) {
  const [incluirEncerrados, setIncluirEncerrados] = useState(false)
  const { dados: professores, erro, carregando, recarregar } = useCarga(
    () => ebdApi.professores(classeId, incluirEncerrados),
    [classeId, incluirEncerrados],
  )
  const [aviso, setAviso] = useState<string | null>(null)
  const [adicionando, setAdicionando] = useState(false)
  const [encerrando, setEncerrando] = useState<EbdProfessor | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [erroAcao, setErroAcao] = useState<string | null>(null)

  async function encerrar() {
    if (!encerrando) return
    setOcupado(true)
    setErroAcao(null)
    try {
      await ebdApi.encerrarProfessor(classeId, encerrando.id, hojeLocal())
      setAviso(`${encerrando.nome} deixou de ser professor(a) desta classe.`)
      setEncerrando(null)
      recarregar()
      onMudou()
    } catch (err) {
      setErroAcao(err instanceof ApiError ? err.message : 'Não foi possível encerrar.')
    } finally {
      setOcupado(false)
    }
  }

  if (erro && !professores) return <p className="aviso erro" role="alert">{erro}</p>
  if (!professores) return <Carregando />

  return (
    <div>
      <div className="titulo-linha">
        <label className="marcador">
          <input type="checkbox" checked={incluirEncerrados} onChange={(e) => setIncluirEncerrados(e.target.checked)} />
          Mostrar quem já deixou a classe
        </label>
        {gestor && (
          <button
            type="button"
            className="botao"
            disabled={!ativa}
            onClick={() => {
              setAviso(null)
              setAdicionando(true)
            }}
          >
            Adicionar professor
          </button>
        )}
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}
      {erro && <p className="aviso erro" role="alert">{erro}</p>}

      <div className="tabela-wrap" aria-busy={carregando}>
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Desde</th>
              <th>Situação</th>
              {gestor && <th>Ações</th>}
            </tr>
          </thead>
          <tbody>
            {professores.map((p) => (
              <tr key={p.id}>
                <td>{p.nome}</td>
                <td>{formatarData(p.inicio)}</td>
                <td>
                  {p.fim ? (
                    <span className="selo">Até {formatarData(p.fim)}</span>
                  ) : (
                    <span className="selo ativo">Em exercício</span>
                  )}
                </td>
                {gestor && (
                  <td className="acoes">
                    {!p.fim && (
                      <button
                        type="button"
                        className="botao secundario pequeno"
                        aria-label={`Encerrar ${p.nome}`}
                        onClick={() => setEncerrando(p)}
                      >
                        Encerrar
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {professores.length === 0 && (
              <tr>
                <td colSpan={gestor ? 4 : 3} className="vazio">Nenhum professor.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {adicionando && (
        <AdicionarProfessorDialogo
          classeId={classeId}
          onFechar={() => setAdicionando(false)}
          onAdicionado={(novo) => {
            setAdicionando(false)
            setAviso(`${novo.nome} agora é professor(a) desta classe.`)
            recarregar()
            onMudou()
          }}
        />
      )}

      <DialogoConfirmar
        aberto={encerrando !== null}
        titulo="Encerrar como professor?"
        rotuloConfirmar="Encerrar"
        rotuloOcupado="Encerrando…"
        ocupado={ocupado}
        erro={erroAcao}
        onConfirmar={encerrar}
        onCancelar={() => {
          setEncerrando(null)
          setErroAcao(null)
        }}
      >
        <p>
          <strong>{encerrando?.nome}</strong> deixa de ser professor(a) desta classe e perde o acesso a ela. O histórico é
          mantido.
        </p>
      </DialogoConfirmar>
    </div>
  )
}
