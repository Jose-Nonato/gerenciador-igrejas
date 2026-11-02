import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { sociedadesApi } from '../api/endpoints'
import type { Socio, TipoSocio } from '../api/types'
import { TIPO_SOCIO } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'
import { Dialogo } from './Dialogo'
import { SeletorMembro } from './SeletorMembro'

interface Props {
  sociedadeId: string
  onAdicionado: (socio: Socio) => void
  onFechar: () => void
}

export function AdicionarSocioDialogo({ sociedadeId, onAdicionado, onFechar }: Props) {
  const [tipo, setTipo] = useState<TipoSocio>('ativo')
  const [membroId, setMembroId] = useState<string | null>(null)
  const [nomeMembro, setNomeMembro] = useState<string | null>(null)
  const [nomeExterno, setNomeExterno] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const externo = tipo === 'nao_membro'

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (externo && !nomeExterno.trim()) return setErro('Informe o nome do não membro.')
    if (!externo && !membroId) return setErro('Escolha o membro na busca.')
    setErro(null)
    setEnviando(true)
    try {
      onAdicionado(
        await sociedadesApi.adicionarSocio(
          sociedadeId,
          externo ? { tipo, nome_externo: nomeExterno.trim() } : { tipo, membro_id: membroId },
        ),
      )
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível adicionar o sócio.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Adicionar sócio" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <CampoSelect
          rotulo="Tipo"
          value={tipo}
          onChange={(e) => setTipo(e.target.value as TipoSocio)}
          ajuda={externo ? 'Visitante frequente: só o nome, sem vínculo com o rol.' : 'Precisa ser membro da igreja.'}
        >
          {Object.entries(TIPO_SOCIO).map(([v, r]) => (
            <option key={v} value={v}>{r}</option>
          ))}
        </CampoSelect>

        {externo ? (
          <Campo
            rotulo="Nome *"
            value={nomeExterno}
            onChange={(e) => setNomeExterno(e.target.value)}
            maxLength={255}
            autoFocus
          />
        ) : (
          <SeletorMembro
            rotulo="Membro"
            // Busca restrita: quem lidera a sociedade pode não ter acesso ao rol
            buscar={(q) => sociedadesApi.buscarMembros(sociedadeId, q)}
            nomeSelecionado={membroId ? nomeMembro : null}
            onSelecionar={(m) => {
              setMembroId(m?.id ?? null)
              setNomeMembro(m?.nome ?? null)
            }}
          />
        )}

        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Adicionando…' : 'Adicionar sócio'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}
