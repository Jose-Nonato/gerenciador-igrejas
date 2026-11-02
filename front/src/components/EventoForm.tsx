import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import type { FormaRecepcao, Membro, NovoEvento, Oficio, SituacaoMembro, TipoEvento } from '../api/types'
import { EFEITO_EVENTO, eventosPermitidos, exigeAta } from '../regrasEventos'
import { FORMA_RECEPCAO, SITUACAO, TIPO_EVENTO } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'

const hoje = () => new Date().toISOString().slice(0, 10)
const vazioParaNulo = (v: string) => (v.trim() === '' ? null : v.trim())

// Motivos de saída aceitos pelo backend (controllers/regras_rol.py)
const MOTIVOS_SAIDA: SituacaoMembro[] = ['transferido', 'falecido', 'excluido']

interface Props {
  membro: Membro
  onRegistrar: (dados: NovoEvento) => Promise<void>
  onCancelar: () => void
}

export function EventoForm({ membro, onRegistrar, onCancelar }: Props) {
  const tipos = eventosPermitidos(membro)
  const [tipo, setTipo] = useState<TipoEvento>(tipos[0])
  const [data, setData] = useState(hoje())
  const [ata, setAta] = useState('')
  const [forma, setForma] = useState<FormaRecepcao | ''>('')
  const [igreja, setIgreja] = useState('')
  const [observacao, setObservacao] = useState('')
  const [oficio, setOficio] = useState<Oficio | ''>('')
  const [motivo, setMotivo] = useState<SituacaoMembro | ''>('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!data) return setErro('Informe a data do evento.')
    if (data > hoje()) return setErro('A data do evento não pode estar no futuro.')
    if (exigeAta(tipo) && !ata.trim()) return setErro('Informe a ata do Conselho.')
    if (tipo === 'recepcao' && !forma) return setErro('Informe a forma de recepção.')
    if (tipo === 'ordenacao' && !oficio) return setErro('Informe o ofício: presbítero ou diácono.')
    if (tipo === 'saida' && !motivo) return setErro('Informe o motivo da saída.')

    setErro(null)
    setEnviando(true)
    try {
      await onRegistrar({
        tipo,
        data,
        ata_conselho: vazioParaNulo(ata),
        igreja_relacionada: vazioParaNulo(igreja),
        observacao: vazioParaNulo(observacao),
        // Só os campos que se aplicam ao tipo: o backend recusa os demais
        forma_recepcao: tipo === 'recepcao' ? forma || null : null,
        oficio: tipo === 'ordenacao' ? oficio || null : null,
        situacao_resultante: tipo === 'saida' ? motivo || null : null,
      })
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível registrar o evento.')
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={enviar} noValidate className="evento-form">
      <h2>Registrar evento eclesiástico</h2>
      <div className="grade">
        <CampoSelect rotulo="Tipo de evento *" value={tipo} onChange={(e) => setTipo(e.target.value as TipoEvento)}>
          {tipos.map((t) => (
            <option key={t} value={t}>{TIPO_EVENTO[t]}</option>
          ))}
        </CampoSelect>
        <Campo rotulo="Data *" type="date" max={hoje()} value={data} onChange={(e) => setData(e.target.value)} required />
      </div>
      <p className="ajuda efeito">{EFEITO_EVENTO[tipo]}</p>

      {tipo === 'recepcao' && (
        <CampoSelect rotulo="Forma de recepção *" value={forma} onChange={(e) => setForma(e.target.value as FormaRecepcao | '')}>
          <option value="">Selecione…</option>
          {Object.entries(FORMA_RECEPCAO).map(([v, r]) => (
            <option key={v} value={v}>{r}</option>
          ))}
        </CampoSelect>
      )}
      {tipo === 'ordenacao' && (
        <CampoSelect rotulo="Ofício conferido *" value={oficio} onChange={(e) => setOficio(e.target.value as Oficio | '')}>
          <option value="">Selecione…</option>
          <option value="presbitero">Presbítero</option>
          <option value="diacono">Diácono</option>
        </CampoSelect>
      )}
      {tipo === 'saida' && (
        <CampoSelect rotulo="Motivo da saída *" value={motivo} onChange={(e) => setMotivo(e.target.value as SituacaoMembro | '')}>
          <option value="">Selecione…</option>
          {MOTIVOS_SAIDA.map((m) => (
            <option key={m} value={m}>{SITUACAO[m]}</option>
          ))}
        </CampoSelect>
      )}

      <Campo
        rotulo={exigeAta(tipo) ? 'Ata do Conselho *' : 'Ata do Conselho'}
        value={ata}
        onChange={(e) => setAta(e.target.value)}
        maxLength={255}
        ajuda={exigeAta(tipo) ? undefined : 'O batismo pode ser registrado sem ata.'}
      />
      <Campo
        rotulo="Igreja relacionada"
        value={igreja}
        onChange={(e) => setIgreja(e.target.value)}
        maxLength={255}
        ajuda="Ex.: igreja de origem ou de destino."
      />
      <div className="campo">
        <label htmlFor="ev-obs">Observação</label>
        <textarea id="ev-obs" rows={3} value={observacao} onChange={(e) => setObservacao(e.target.value)} />
      </div>

      {erro && <p className="aviso erro" role="alert">{erro}</p>}
      <div className="acoes-form">
        <button type="submit" className="botao" disabled={enviando}>
          {enviando ? 'Registrando…' : 'Registrar evento'}
        </button>
        <button type="button" className="botao secundario" onClick={onCancelar} disabled={enviando}>
          Cancelar
        </button>
      </div>
    </form>
  )
}
