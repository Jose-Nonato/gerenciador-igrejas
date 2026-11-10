import { Link, useLocation } from 'react-router-dom'
import { ebdApi } from '../api/endpoints'
import { formatarData } from '../formatar'
import { useCarga } from '../useCarga'
import { Carregando } from './Carregando'

export function EbdAulasTab({ classeId, ativa }: { classeId: string; ativa: boolean }) {
  const aviso = (useLocation().state as { aviso?: string } | null)?.aviso
  const { dados: aulas, erro } = useCarga(() => ebdApi.aulas(classeId), [classeId])

  if (erro && !aulas) return <p className="aviso erro" role="alert">{erro}</p>
  if (!aulas) return <Carregando />

  return (
    <div>
      <div className="titulo-linha">
        <p className="subtitulo">
          {aulas.length} {aulas.length === 1 ? 'aula registrada' : 'aulas registradas'}
        </p>
        {ativa && <Link to={`/ebd/${classeId}/aulas/nova`} className="botao">Nova aula</Link>}
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}

      <div className="tabela-wrap">
        <table>
          <thead>
            <tr>
              <th>Data</th>
              <th>Lição</th>
              <th>Presentes</th>
              <th>Ausentes</th>
              <th>Justificados</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {aulas.map((a) => (
              <tr key={a.id}>
                <td>{formatarData(a.data)}</td>
                <td>{a.licao ?? '—'}</td>
                <td>{a.presentes}</td>
                <td>{a.ausentes}</td>
                <td>{a.justificados}</td>
                <td className="acoes">
                  <Link
                    to={`/ebd/${classeId}/aulas/${a.id}`}
                    className="botao secundario pequeno"
                    aria-label={`Abrir aula de ${formatarData(a.data)}`}
                  >
                    Abrir
                  </Link>
                </td>
              </tr>
            ))}
            {aulas.length === 0 && (
              <tr>
                <td colSpan={6} className="vazio">Nenhuma aula registrada.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
