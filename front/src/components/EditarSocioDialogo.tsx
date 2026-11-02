import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { sociedadesApi } from '../api/endpoints'
import type { AtualizacaoSocio, Socio, TipoSocio } from '../api/types'
import { TIPO_SOCIO } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'
import { Dialogo } from './Dialogo'

interface Props {
  socio: Socio
  onSalvo: (socio: Socio) => void
  onFechar: () => void
}

export function EditarSocioDialogo({ socio, onSalvo, onFechar }: Props) {
  const externo = socio.tipo === 'nao_membro'
  const [tipo, setTipo] = useState<TipoSocio>(socio.tipo)
  const [nome, setNome] = useState(socio.nome)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  // Só o que mudou; o backend recusa PATCH vazio
  const mudancas: AtualizacaoSocio = {}
  if (!externo && tipo !== socio.tipo) mudancas.tipo = tipo
  if (externo && nome.trim() !== socio.nome) mudancas.nome_externo = nome.trim()
  const alterado = Object.keys(mudancas).length > 0

  async function salvar(e: FormEvent) {
    e.preventDefault()
    if (externo && !nome.trim()) return setErro('Informe o nome.')
    if (!alterado) return
    setErro(null)
    setEnviando(true)
    try {
      onSalvo(await sociedadesApi.atualizarSocio(socio.sociedade_id, socio.id, mudancas))
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo={`Alterar ${socio.nome}`} onFechar={onFechar}>
      <form onSubmit={salvar} noValidate>
        {externo ? (
          <Campo rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={255} autoFocus />
        ) : (
          <CampoSelect
            rotulo="Tipo"
            value={tipo}
            onChange={(e) => setTipo(e.target.value as TipoSocio)}
            ajuda="Alternar entre sócio ativo e cooperador. Para mudar quem é o sócio, remova e adicione de novo."
          >
            <option value="ativo">{TIPO_SOCIO.ativo}</option>
            <option value="cooperador">{TIPO_SOCIO.cooperador}</option>
          </CampoSelect>
        )}
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando || !alterado}>
            {enviando ? 'Salvando…' : 'Salvar'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}
