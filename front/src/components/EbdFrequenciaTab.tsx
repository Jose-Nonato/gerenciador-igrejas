import { useState } from 'react'
import { ebdApi } from '../api/endpoints'
import { hojeLocal } from '../formatar'
import { useCarga } from '../useCarga'
import { Campo } from './Campo'
import { Carregando } from './Carregando'

function percentual(v: number | null): string {
  return v === null ? '—' : `${v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 1 })}%`
}

export function EbdFrequenciaTab({ classeId }: { classeId: string }) {
  const [de, setDe] = useState('')
  const [ate, setAte] = useState('')
  const periodoInvalido = de !== '' && ate !== '' && de > ate

  const { dados, erro, carregando } = useCarga(
    () => ebdApi.frequencia(classeId, de || undefined, ate || undefined),
    [classeId, periodoInvalido ? '' : de, periodoInvalido ? '' : ate],
  )

  return (
    <div>
      <div className="filtros">
        <Campo rotulo="De" type="date" max={hojeLocal()} value={de} onChange={(e) => setDe(e.target.value)} />
        <Campo rotulo="Até" type="date" max={hojeLocal()} value={ate} onChange={(e) => setAte(e.target.value)} />
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
            {dados.total_aulas} {dados.total_aulas === 1 ? 'aula' : 'aulas'} no período. O percentual conta os presentes
            sobre as aulas com presença lançada; as demais aparecem em “Sem registro”.
          </p>
          <div className="tabela-wrap" aria-busy={carregando}>
            <table>
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Presentes</th>
                  <th>Ausentes</th>
                  <th>Justificados</th>
                  <th>Sem registro</th>
                  <th>Frequência</th>
                </tr>
              </thead>
              <tbody>
                {dados.alunos.map((a) => (
                  <tr key={a.aluno_id}>
                    <td>{a.nome}</td>
                    <td>{a.presentes}</td>
                    <td>{a.ausentes}</td>
                    <td>{a.justificados}</td>
                    <td>{a.sem_registro}</td>
                    <td><strong>{percentual(a.percentual_presenca)}</strong></td>
                  </tr>
                ))}
                {dados.alunos.length === 0 && (
                  <tr>
                    <td colSpan={6} className="vazio">Nenhum aluno com dados no período.</td>
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
