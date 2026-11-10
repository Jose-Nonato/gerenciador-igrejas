import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { sociedadesApi } from '../api/endpoints'
import type { CargoLideranca, Lideranca } from '../api/types'
import { CARGO } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'
import { Dialogo } from './Dialogo'
import { SeletorMembro } from './SeletorMembro'
import { hojeLocal as hoje } from '../formatar'

interface Props {
  sociedadeId: string
  onAdicionada: (item: Lideranca) => void
  onFechar: () => void
}

export function AdicionarLiderancaDialogo({ sociedadeId, onAdicionada, onFechar }: Props) {
  const [cargo, setCargo] = useState<CargoLideranca>('presidente')
  const [descricao, setDescricao] = useState('')
  const [membroId, setMembroId] = useState<string | null>(null)
  const [nomeMembro, setNomeMembro] = useState<string | null>(null)
  const [inicio, setInicio] = useState(hoje())
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!membroId) return setErro('Escolha o membro na busca.')
    if (cargo === 'outro' && !descricao.trim()) return setErro('Descreva o cargo.')
    if (!inicio) return setErro('Informe a data de início do mandato.')
    if (inicio > hoje()) return setErro('A data de início não pode estar no futuro.')

    setErro(null)
    setEnviando(true)
    try {
      onAdicionada(
        await sociedadesApi.adicionarLideranca(sociedadeId, {
          membro_id: membroId,
          cargo,
          cargo_descricao: cargo === 'outro' ? descricao.trim() : null,
          inicio,
        }),
      )
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível registrar a liderança.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Adicionar à diretoria" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <CampoSelect
          rotulo="Cargo"
          value={cargo}
          onChange={(e) => setCargo(e.target.value as CargoLideranca)}
          ajuda="Presidente, vice, secretário e tesoureiro têm um ocupante por vez; para trocar, encerre o mandato atual antes."
        >
          {Object.entries(CARGO).map(([v, r]) => (
            <option key={v} value={v}>{r}</option>
          ))}
        </CampoSelect>
        {cargo === 'outro' && (
          <Campo
            rotulo="Descrição do cargo *"
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            maxLength={100}
            ajuda="Ex.: Diretor de música."
          />
        )}
        <SeletorMembro
          rotulo="Membro"
          nomeSelecionado={membroId ? nomeMembro : null}
          onSelecionar={(m) => {
            setMembroId(m?.id ?? null)
            setNomeMembro(m?.nome ?? null)
          }}
        />
        <Campo
          rotulo="Início do mandato"
          type="date"
          max={hoje()}
          value={inicio}
          onChange={(e) => setInicio(e.target.value)}
          ajuda="A pessoa precisa ser membro da igreja, mas não precisa ser sócia da sociedade."
        />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Adicionar'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}
