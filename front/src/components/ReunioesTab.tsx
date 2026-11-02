import { Link, useLocation } from 'react-router-dom'
import { sociedadesApi } from '../api/endpoints'
import { formatarData } from '../formatar'
import { useCarga } from '../useCarga'
import { Carregando } from './Carregando'

export function ReunioesTab({ sociedadeId }: { sociedadeId: string }) {
  const aviso = (useLocation().state as { aviso?: string } | null)?.aviso
  const { dados: reunioes, erro } = useCarga(() => sociedadesApi.reunioes(sociedadeId), [sociedadeId])

  if (erro && !reunioes) return <p className="aviso erro" role="alert">{erro}</p>
  if (!reunioes) return <Carregando />

  return (
    <div>
      <div className="titulo-linha">
        <p className="subtitulo">
          {reunioes.length} {reunioes.length === 1 ? 'reunião registrada' : 'reuniões registradas'}
        </p>
        <Link to={`/sociedades/${sociedadeId}/reunioes/nova`} className="botao">Nova reunião</Link>
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}

      <div className="tabela-wrap">
        <table>
          <thead>
            <tr>
              <th>Data</th>
              <th>Tema</th>
              <th>Presentes</th>
              <th>Ausentes</th>
              <th>Justificados</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {reunioes.map((r) => (
              <tr key={r.id}>
                <td>{formatarData(r.data)}</td>
                <td>{r.tema ?? '—'}</td>
                <td>{r.presentes}</td>
                <td>{r.ausentes}</td>
                <td>{r.justificados}</td>
                <td className="acoes">
                  <Link
                    to={`/sociedades/${sociedadeId}/reunioes/${r.id}`}
                    className="botao secundario pequeno"
                    aria-label={`Abrir reunião de ${formatarData(r.data)}`}
                  >
                    Abrir
                  </Link>
                </td>
              </tr>
            ))}
            {reunioes.length === 0 && (
              <tr>
                <td colSpan={6} className="vazio">Nenhuma reunião registrada.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
