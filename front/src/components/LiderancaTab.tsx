import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { sociedadesApi } from '../api/endpoints'
import type { Lideranca } from '../api/types'
import { formatarData, hojeLocal as hoje } from '../formatar'
import { CARGO } from '../rotulos'
import { useAcessoSociedades } from '../useAcessoSociedades'
import { useCarga } from '../useCarga'
import { AdicionarLiderancaDialogo } from './AdicionarLiderancaDialogo'
import { Campo } from './Campo'
import { Carregando } from './Carregando'
import { DialogoConfirmar } from './DialogoConfirmar'

const nomeDoCargo = (l: Lideranca) => (l.cargo === 'outro' ? (l.cargo_descricao ?? CARGO.outro) : CARGO[l.cargo])

export function LiderancaTab({ sociedadeId }: { sociedadeId: string }) {
  // Só admin e pastor alteram a diretoria; quem lidera a sociedade apenas consulta
  const { gestor, verFichas } = useAcessoSociedades()
  const [incluirEncerrados, setIncluirEncerrados] = useState(false)
  const { dados: itens, erro, carregando, recarregar } = useCarga(
    () => sociedadesApi.lideranca(sociedadeId, incluirEncerrados),
    [sociedadeId, incluirEncerrados],
  )
  const [aviso, setAviso] = useState<string | null>(null)
  const [adicionando, setAdicionando] = useState(false)
  const [encerrando, setEncerrando] = useState<Lideranca | null>(null)
  const [fim, setFim] = useState(hoje())
  const [ocupado, setOcupado] = useState(false)
  const [erroEncerrar, setErroEncerrar] = useState<string | null>(null)

  async function encerrar() {
    if (!encerrando) return
    if (!fim) return setErroEncerrar('Informe a data de término.')
    if (fim > hoje()) return setErroEncerrar('A data de término não pode estar no futuro.')
    setOcupado(true)
    setErroEncerrar(null)
    try {
      await sociedadesApi.encerrarLideranca(sociedadeId, encerrando.id, fim)
      setAviso(`Mandato de ${encerrando.nome} (${nomeDoCargo(encerrando)}) encerrado.`)
      setEncerrando(null)
      recarregar()
    } catch (err) {
      setErroEncerrar(err instanceof ApiError ? err.message : 'Não foi possível encerrar o mandato.')
    } finally {
      setOcupado(false)
    }
  }

  if (erro && !itens) return <p className="aviso erro" role="alert">{erro}</p>
  if (!itens) return <Carregando />

  return (
    <div>
      <div className="titulo-linha">
        <label className="marcador">
          <input type="checkbox" checked={incluirEncerrados} onChange={(e) => setIncluirEncerrados(e.target.checked)} />
          Mostrar mandatos encerrados
        </label>
        {gestor && (
          <button
            type="button"
            className="botao"
            onClick={() => {
              setAviso(null)
              setAdicionando(true)
            }}
          >
            Adicionar à diretoria
          </button>
        )}
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}
      {erro && <p className="aviso erro" role="alert">{erro}</p>}

      {!gestor && (
        <p className="ajuda">Somente o administrador e o pastor alteram a diretoria.</p>
      )}

      <div className="tabela-wrap" aria-busy={carregando}>
        <table>
          <thead>
            <tr>
              <th>Cargo</th>
              <th>Nome</th>
              <th>Início</th>
              <th>Situação</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {itens.map((l) => (
              <tr key={l.id}>
                <td>{nomeDoCargo(l)}</td>
                <td>
                  {verFichas ? <Link to={`/membros/${l.membro_id}`} className="link-nome">{l.nome}</Link> : l.nome}
                </td>
                <td>{formatarData(l.inicio)}</td>
                <td>
                  {l.fim ? (
                    <span className="selo">Até {formatarData(l.fim)}</span>
                  ) : (
                    <span className="selo ativo">Em exercício</span>
                  )}
                </td>
                <td className="acoes">
                  {gestor && !l.fim && (
                    <button
                      type="button"
                      className="botao secundario pequeno"
                      aria-label={`Encerrar mandato de ${l.nome}`}
                      onClick={() => {
                        setAviso(null)
                        setFim(hoje())
                        setEncerrando(l)
                      }}
                    >
                      Encerrar mandato
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {itens.length === 0 && (
              <tr>
                <td colSpan={5} className="vazio">Nenhuma liderança registrada.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {adicionando && (
        <AdicionarLiderancaDialogo
          sociedadeId={sociedadeId}
          onFechar={() => setAdicionando(false)}
          onAdicionada={(nova) => {
            setAdicionando(false)
            setAviso(`${nova.nome} registrado(a) como ${nomeDoCargo(nova).toLowerCase()}.`)
            recarregar()
          }}
        />
      )}

      <DialogoConfirmar
        aberto={encerrando !== null}
        titulo="Encerrar mandato?"
        rotuloConfirmar="Encerrar mandato"
        rotuloOcupado="Encerrando…"
        ocupado={ocupado}
        erro={erroEncerrar}
        onConfirmar={encerrar}
        onCancelar={() => {
          setEncerrando(null)
          setErroEncerrar(null)
        }}
      >
        <p>
          <strong>{encerrando?.nome}</strong> deixa o cargo de {encerrando ? nomeDoCargo(encerrando).toLowerCase() : ''}.
          O registro permanece no histórico.
        </p>
        <Campo rotulo="Data de término" type="date" max={hoje()} value={fim} onChange={(e) => setFim(e.target.value)} />
      </DialogoConfirmar>
    </div>
  )
}
