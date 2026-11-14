import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { agendaOficialApi } from '../api/endpoints'
import { formatarData, hojeLocal } from '../formatar'
import { useCarga } from '../useCarga'
import { Campo } from './Campo'
import { Carregando } from './Carregando'
import { Dialogo } from './Dialogo'

function NovoBloqueioDialogo({
  onCriado,
  onFechar,
}: {
  onCriado: (afetados: number) => void
  onFechar: () => void
}) {
  const [de, setDe] = useState(hojeLocal())
  const [ate, setAte] = useState(hojeLocal())
  const [motivo, setMotivo] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!de || !ate) return setErro('Informe o primeiro e o último dia.')
    if (ate < de) return setErro('O último dia não pode ser antes do primeiro.')
    setErro(null)
    setEnviando(true)
    try {
      const criado = await agendaOficialApi.criarBloqueio({ de, ate, motivo: motivo.trim() || null })
      onCriado(criado.atendimentos_afetados)
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar a ausência.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Nova ausência" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <Campo rotulo="Primeiro dia" type="date" value={de} onChange={(e) => setDe(e.target.value)} />
        <Campo rotulo="Último dia" type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
        <Campo
          rotulo="Motivo (opcional)"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          maxLength={200}
          ajuda="Só você vê. Ex.: férias, congresso."
        />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Salvar ausência'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}

/** Períodos em que o oficial não atende: os dias deixam de oferecer horários. */
export function BloqueiosSecao() {
  const { dados, erro, recarregar } = useCarga(() => agendaOficialApi.bloqueios(), [])
  const [criando, setCriando] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const [erroAcao, setErroAcao] = useState<string | null>(null)

  async function remover(id: string) {
    setErroAcao(null)
    try {
      await agendaOficialApi.removerBloqueio(id)
      recarregar()
    } catch (err) {
      setErroAcao(err instanceof ApiError ? err.message : 'Não foi possível remover a ausência.')
    }
  }

  if (erro && !dados) return <p className="aviso erro" role="alert">{erro}</p>
  if (!dados) return <Carregando />

  return (
    <div>
      <div className="titulo-linha">
        <h2 className="subtitulo-h2">Ausências</h2>
        <button type="button" className="botao secundario" onClick={() => setCriando(true)}>
          Nova ausência
        </button>
      </div>
      <p className="subtitulo">Nos dias de ausência ninguém consegue pedir conversa com você.</p>

      {aviso && <p className="aviso atencao" role="status">{aviso}</p>}
      {erroAcao && <p className="aviso erro" role="alert">{erroAcao}</p>}

      {dados.length === 0 ? (
        <p className="vazio-texto">Nenhuma ausência marcada.</p>
      ) : (
        <div className="tabela-wrap">
          <table>
            <thead>
              <tr>
                <th>Período</th>
                <th>Motivo</th>
                <th>Conversas no período</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {dados.map((b) => (
                <tr key={b.id}>
                  <td>{b.de === b.ate ? formatarData(b.de) : `${formatarData(b.de)} a ${formatarData(b.ate)}`}</td>
                  <td>{b.motivo ?? '—'}</td>
                  <td>
                    {b.atendimentos_afetados === 0 ? (
                      '—'
                    ) : (
                      <span className="selo status-atendimento-remarcacao">{b.atendimentos_afetados} em aberto</span>
                    )}
                  </td>
                  <td className="acoes">
                    <button type="button" className="botao secundario" onClick={() => remover(b.id)}>
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {criando && (
        <NovoBloqueioDialogo
          onFechar={() => setCriando(false)}
          onCriado={(afetados) => {
            setCriando(false)
            setAviso(
              afetados > 0
                ? `Há ${afetados} ${afetados === 1 ? 'conversa em aberto' : 'conversas em aberto'} nesse período. Elas continuam valendo: remarque ou cancele em "Pedidos recebidos".`
                : null,
            )
            recarregar()
          }}
        />
      )}
    </div>
  )
}
