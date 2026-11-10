import { useState } from 'react'
import { sociedadesApi } from '../api/endpoints'
import { TIPO_SOCIO } from '../rotulos'
import { useCarga } from '../useCarga'
import { Campo } from './Campo'
import { Carregando } from './Carregando'
import { hojeLocal as hoje } from '../formatar'

function percentual(v: number | null): string {
  return v === null ? '—' : `${v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 1 })}%`
}

export function FrequenciaTab({ sociedadeId }: { sociedadeId: string }) {
  const [de, setDe] = useState('')
  const [ate, setAte] = useState('')
  const periodoInvalido = de !== '' && ate !== '' && de > ate

  const { dados, erro, carregando } = useCarga(
    () => sociedadesApi.frequencia(sociedadeId, de || undefined, ate || undefined),
    [sociedadeId, periodoInvalido ? '' : de, periodoInvalido ? '' : ate],
  )

  return (
    <div>
      <div className="filtros">
        <Campo rotulo="De" type="date" max={hoje()} value={de} onChange={(e) => setDe(e.target.value)} />
        <Campo rotulo="Até" type="date" max={hoje()} value={ate} onChange={(e) => setAte(e.target.value)} />
        <div className="campo">
          <span className="rotulo-falso" aria-hidden="true">&nbsp;</span>
          <button
            type="button"
            className="botao secundario"
            onClick={() => {
              setDe('')
              setAte('')
            }}
            disabled={!de && !ate}
          >
            Todo o período
          </button>
        </div>
      </div>

      {periodoInvalido && <p className="aviso erro" role="alert">A data inicial não pode ser depois da final.</p>}
      {erro && !periodoInvalido && <p className="aviso erro" role="alert">{erro}</p>}
      {!dados && !erro && <Carregando />}

      {dados && (
        <>
          <p className="subtitulo">
            {dados.total_reunioes} {dados.total_reunioes === 1 ? 'reunião' : 'reuniões'} no período. O percentual conta
            os presentes sobre as reuniões com presença lançada; as demais aparecem em “Sem registro”.
          </p>
          <div className="tabela-wrap" aria-busy={carregando}>
            <table>
              <thead>
                <tr>
                  <th>Sócio</th>
                  <th>Tipo</th>
                  <th>Presentes</th>
                  <th>Ausentes</th>
                  <th>Justificados</th>
                  <th>Sem registro</th>
                  <th>Frequência</th>
                </tr>
              </thead>
              <tbody>
                {dados.socios.map((s) => (
                  <tr key={s.socio_id}>
                    <td>{s.nome}</td>
                    <td>{TIPO_SOCIO[s.tipo]}</td>
                    <td>{s.presentes}</td>
                    <td>{s.ausentes}</td>
                    <td>{s.justificados}</td>
                    <td>{s.sem_registro}</td>
                    <td><strong>{percentual(s.percentual_presenca)}</strong></td>
                  </tr>
                ))}
                {dados.socios.length === 0 && (
                  <tr>
                    <td colSpan={7} className="vazio">Nenhum sócio com dados no período.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
