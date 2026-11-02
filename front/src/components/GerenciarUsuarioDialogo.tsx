import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { usuariosApi } from '../api/endpoints'
import type { AtualizacaoUsuario, Perfil, StatusUsuario, Usuario } from '../api/types'
import { PERFIL, STATUS_USUARIO } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'
import { Dialogo } from './Dialogo'
import { SeletorMembro } from './SeletorMembro'

// Estados que o admin pode atribuir; convite_pendente só nasce do convite
const STATUS_ATRIBUIVEIS: StatusUsuario[] = ['ativo', 'bloqueado', 'desativado']

interface Props {
  usuario: Usuario
  /** O backend não deixa o admin mudar o próprio perfil, status ou e-mail */
  ehProprio: boolean
  nomeMembro: string | null
  onSalvo: (usuario: Usuario, nomeMembro: string | null) => void
  onFechar: () => void
}

export function GerenciarUsuarioDialogo({
  usuario,
  ehProprio,
  nomeMembro,
  onSalvo,
  onFechar,
}: Props) {
  const pendente = usuario.status === 'convite_pendente'
  const [email, setEmail] = useState(usuario.email)
  const [perfil, setPerfil] = useState<Perfil>(usuario.perfil)
  const [status, setStatus] = useState<StatusUsuario>(usuario.status)
  const [membroId, setMembroId] = useState<string | null>(usuario.membro_id)
  const [nomeEscolhido, setNomeEscolhido] = useState<string | null>(nomeMembro)
  const [erro, setErro] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  // Só vai o que mudou: o backend recusa PATCH vazio e audita cada alteração
  const mudancas: AtualizacaoUsuario = {}
  if (email.trim().toLowerCase() !== usuario.email) mudancas.email = email.trim()
  if (perfil !== usuario.perfil) mudancas.perfil = perfil
  if (status !== usuario.status) mudancas.status = status
  if (membroId !== usuario.membro_id) mudancas.membro_id = membroId
  const alterado = Object.keys(mudancas).length > 0
  const derrubaSessoes = 'email' in mudancas || 'perfil' in mudancas || (status !== 'ativo' && 'status' in mudancas)

  async function salvar(e: FormEvent) {
    e.preventDefault()
    if (!alterado) return
    setErro(null)
    setEnviando(true)
    try {
      onSalvo(await usuariosApi.atualizar(usuario.id, mudancas), nomeEscolhido)
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar as alterações.')
      setEnviando(false)
    }
  }

  async function reenviar() {
    setErro(null)
    setAviso(null)
    setEnviando(true)
    try {
      await usuariosApi.reenviarConvite(usuario.id)
      setAviso('Novo convite enviado. O link anterior deixou de valer.')
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível reenviar o convite.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Gerenciar usuário" onFechar={onFechar}>
      <form onSubmit={salvar} noValidate>
        {ehProprio && (
          <p className="ajuda dialogo-texto">
            Esta é a sua conta: perfil, status e e-mail não podem ser alterados aqui. Você pode vincular o seu cadastro
            de membro.
          </p>
        )}
        <Campo
          rotulo="E-mail"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={ehProprio}
          ajuda={pendente ? 'Corrigir o e-mail reenvia o convite ao novo endereço.' : undefined}
        />
        <div className="grade">
          <CampoSelect rotulo="Perfil" value={perfil} onChange={(e) => setPerfil(e.target.value as Perfil)} disabled={ehProprio}>
            {Object.entries(PERFIL).map(([v, r]) => (
              <option key={v} value={v}>{r}</option>
            ))}
          </CampoSelect>
          <CampoSelect
            rotulo="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value as StatusUsuario)}
            disabled={ehProprio || pendente}
            ajuda={pendente ? 'Ainda não ativou a conta pelo convite.' : undefined}
          >
            {pendente && <option value="convite_pendente">{STATUS_USUARIO.convite_pendente}</option>}
            {STATUS_ATRIBUIVEIS.map((s) => (
              <option key={s} value={s}>{STATUS_USUARIO[s]}</option>
            ))}
          </CampoSelect>
        </div>

        <SeletorMembro
          nomeSelecionado={membroId ? nomeEscolhido : null}
          onSelecionar={(m) => {
            setMembroId(m?.id ?? null)
            setNomeEscolhido(m?.nome ?? null)
          }}
        />

        {derrubaSessoes && (
          <p className="aviso atencao" role="status">
            Alterar e-mail, perfil ou bloquear/desativar encerra as sessões abertas deste usuário.
          </p>
        )}
        {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}
        {erro && <p className="aviso erro" role="alert">{erro}</p>}

        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando || !alterado}>
            {enviando ? 'Salvando…' : 'Salvar alterações'}
          </button>
          {pendente && (
            <button type="button" className="botao secundario" onClick={reenviar} disabled={enviando}>
              Reenviar convite
            </button>
          )}
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Fechar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}
