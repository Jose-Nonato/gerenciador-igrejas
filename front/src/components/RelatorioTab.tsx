import { agendaOficialApi } from '../api/endpoints'
import { MES_ABREVIADO } from '../rotulos'
import { useCarga } from '../useCarga'
import { Carregando } from './Carregando'

function rotuloMes(mes: string): string {
  const [ano, numero] = mes.split('-')
  return `${MES_ABREVIADO[Number(numero) - 1]}/${ano}`
}

/** Conversas do próprio oficial por mês: só números, nada que identifique alguém. */
export function RelatorioTab() {
  const { dados, erro } = useCarga(() => agendaOficialApi.relatorio(), [])

  if (erro && !dados) return <p className="aviso erro" role="alert">{erro}</p>
  if (!dados) return <Carregando />

  const soma = (campo: 'total' | 'realizados' | 'faltas' | 'cancelados' | 'recusados' | 'em_andamento') =>
    dados.reduce((acc, m) => acc + m[campo], 0)

  if (soma('total') === 0) {
    return <p className="vazio-texto">Nenhuma conversa nos últimos 12 meses.</p>
  }

  return (
    <div>
      <p className="subtitulo">Últimos 12 meses até o fim deste mês, pela data marcada das conversas. Só você vê este relatório.</p>
      <div className="tabela-wrap">
        <table>
          <thead>
            <tr>
              <th>Mês</th>
              <th>Total</th>
              <th>Realizadas</th>
              <th>Não compareceram</th>
              <th>Canceladas</th>
              <th>Recusadas</th>
              <th>Em andamento</th>
            </tr>
          </thead>
          <tbody>
            {[...dados].reverse().map((m) => (
              <tr key={m.mes}>
                <td>{rotuloMes(m.mes)}</td>
                <td>{m.total}</td>
                <td>{m.realizados}</td>
                <td>{m.faltas}</td>
                <td>{m.cancelados}</td>
                <td>{m.recusados}</td>
                <td>{m.em_andamento}</td>
              </tr>
            ))}
            <tr>
              <th>Total</th>
              <th>{soma('total')}</th>
              <th>{soma('realizados')}</th>
              <th>{soma('faltas')}</th>
              <th>{soma('cancelados')}</th>
              <th>{soma('recusados')}</th>
              <th>{soma('em_andamento')}</th>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
