import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { sociedadesApi } from '../api/endpoints'
import type { Socio } from '../api/types'
import { formatarData } from '../formatar'
import { TIPO_SOCIO } from '../rotulos'
import { useCarga } from '../useCarga'
import { AdicionarSocioDialogo } from './AdicionarSocioDialogo'
import { Carregando } from './Carregando'
import { DialogoConfirmar } from './DialogoConfirmar'
import { EditarSocioDialogo } from './EditarSocioDialogo'

interface Props {
  sociedadeId: string
  /** Avisa a página quando o total de sócios mudou (o cabeçalho mostra a contagem) */
  onMudou: () => void
}

export function SociosTab({ sociedadeId, onMudou }: Props) {
  const [incluirEx, setIncluirEx] = useState(false)
  const { dados: socios, erro, carregando, recarregar } = useCarga(
    () => sociedadesApi.socios(sociedadeId, incluirEx),
    [sociedadeId, incluirEx],
  )
  const [aviso, setAviso] = useState<string | null>(null)
  const [adicionando, setAdicionando] = useState(false)
  const [editando, setEditando] = useState<Socio | null>(null)
  const [removendo, setRemovendo] = useState<Socio | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [erroRemocao, setErroRemocao] = useState<string | null>(null)

  async function remover() {
    if (!removendo) return
    setOcupado(true)
    setErroRemocao(null)
    try {
      await sociedadesApi.removerSocio(sociedadeId, removendo.id)
      setAviso(`${removendo.nome} saiu da sociedade.`)
      setRemovendo(null)
      recarregar()
      onMudou()
    } catch (err) {
      setErroRemocao(err instanceof ApiError ? err.message : 'Não foi possível remover o sócio.')
    } finally {
      setOcupado(false)
    }
  }

  if (erro && !socios) return <p className="aviso erro" role="alert">{erro}</p>
  if (!socios) return <Carregando />

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
          onClick={() => {
            setAviso(null)
            setAdicionando(true)
          }}
        >
          Adicionar sócio
        </button>
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}
      {erro && <p className="aviso erro" role="alert">{erro}</p>}

      <div className="tabela-wrap" aria-busy={carregando}>
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Tipo</th>
              <th>Entrou em</th>
              <th>Situação</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {socios.map((s) => (
              <tr key={s.id}>
                <td>
                  {s.membro_id ? (
                    <Link to={`/membros/${s.membro_id}`} className="link-nome">{s.nome}</Link>
                  ) : (
                    s.nome
                  )}
                </td>
                <td>{TIPO_SOCIO[s.tipo]}</td>
                <td>{formatarData(s.entrou_em)}</td>
                <td>
                  {s.saiu_em ? (
                    <span className="selo">Saiu em {formatarData(s.saiu_em)}</span>
                  ) : (
                    <span className="selo ativo">Ativo</span>
                  )}
                </td>
                <td className="acoes">
                  {!s.saiu_em && (
                    <>
                      <button
                        type="button"
                        className="botao secundario pequeno"
                        aria-label={`Alterar ${s.nome}`}
                        onClick={() => {
                          setAviso(null)
                          setEditando(s)
                        }}
                      >
                        Alterar
                      </button>
                      <button
                        type="button"
                        className="botao secundario pequeno"
                        aria-label={`Remover ${s.nome}`}
                        onClick={() => setRemovendo(s)}
                      >
                        Remover
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {socios.length === 0 && (
              <tr>
                <td colSpan={5} className="vazio">Nenhum sócio.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {adicionando && (
        <AdicionarSocioDialogo
          sociedadeId={sociedadeId}
          onFechar={() => setAdicionando(false)}
          onAdicionado={(novo) => {
            setAdicionando(false)
            setAviso(`${novo.nome} foi adicionado(a) à sociedade.`)
            recarregar()
            onMudou()
          }}
        />
      )}

      {editando && (
        <EditarSocioDialogo
          socio={editando}
          onFechar={() => setEditando(null)}
          onSalvo={(atualizado) => {
            setEditando(null)
            setAviso(`${atualizado.nome} atualizado(a).`)
            recarregar()
          }}
        />
      )}

      <DialogoConfirmar
        aberto={removendo !== null}
        titulo="Remover da sociedade?"
        rotuloConfirmar="Remover sócio"
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
          <strong>{removendo?.nome}</strong> deixa de ser sócio(a), mas o histórico de presença é mantido. Se voltar,
          basta adicionar de novo.
        </p>
      </DialogoConfirmar>
    </div>
  )
}
