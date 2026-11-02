import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { sociedadesApi } from '../api/endpoints'
import type { SiglaSociedade, Sociedade } from '../api/types'
import { SIGLA } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'
import { Dialogo } from './Dialogo'

interface Props {
  /** Siglas que a igreja ainda não criou (só pode haver uma sociedade de cada) */
  disponiveis: SiglaSociedade[]
  onCriada: (sociedade: Sociedade) => void
  onFechar: () => void
}

export function NovaSociedadeDialogo({ disponiveis, onCriada, onFechar }: Props) {
  const [sigla, setSigla] = useState<SiglaSociedade>(disponiveis[0])
  const [nome, setNome] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      onCriada(await sociedadesApi.criar(sigla, nome.trim() || null))
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível criar a sociedade.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Nova sociedade" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <CampoSelect rotulo="Sociedade" value={sigla} onChange={(e) => setSigla(e.target.value as SiglaSociedade)}>
          {disponiveis.map((s) => (
            <option key={s} value={s}>{s} — {SIGLA[s]}</option>
          ))}
        </CampoSelect>
        <Campo
          rotulo="Nome de exibição (opcional)"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          maxLength={255}
          ajuda="Ex.: o nome da sua sociedade local. Em branco, usa só a sigla."
        />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Criando…' : 'Criar sociedade'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}
