import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { membrosApi } from '../api/endpoints'
import type { Membro } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Carregando } from '../components/Carregando'
import { DialogoConfirmar } from '../components/DialogoConfirmar'
import { MembroForm } from '../components/MembroForm'
import { podeExcluirMembro } from '../permissoes'

export function EditarMembroPage() {
  const { id } = useParams<{ id: string }>()
  const navegar = useNavigate()
  const { usuario } = useAuth()
  const [membro, setMembro] = useState<Membro | null>(null)
  const [erroCarga, setErroCarga] = useState<string | null>(null)
  const [confirmando, setConfirmando] = useState(false)
  const [excluindo, setExcluindo] = useState(false)
  const [erroExclusao, setErroExclusao] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let ativo = true
    membrosApi
      .obter(id)
      .then((m) => ativo && setMembro(m))
      .catch((err) => ativo && setErroCarga(err instanceof ApiError ? err.message : 'Falha ao carregar o membro.'))
    return () => {
      ativo = false
    }
  }, [id])

  async function excluir() {
    if (!membro) return
    setExcluindo(true)
    setErroExclusao(null)
    try {
      await membrosApi.excluir(membro.id)
      navegar('/membros', { replace: true, state: { aviso: `${membro.nome} foi excluído(a) do rol.` } })
    } catch (err) {
      setErroExclusao(err instanceof ApiError ? err.message : 'Não foi possível excluir o membro.')
      setExcluindo(false)
    }
  }

  if (erroCarga) {
    return (
      <section className="pagina estreita-media">
        <p className="aviso erro" role="alert">{erroCarga}</p>
        <Link to="/membros">← Voltar ao rol</Link>
      </section>
    )
  }
  if (!membro) return <Carregando />

  return (
    <section className="pagina estreita-media">
      <p className="migalha">
        <Link to="/membros">← Rol de membros</Link>
      </p>
      <h1>Editar membro</h1>
      <p className="subtitulo">{membro.nome}</p>

      <MembroForm
        membro={membro}
        rotuloSalvar="Salvar alterações"
        onSalvar={async (dados) => {
          // Rol, situação e ofício não são editáveis aqui: o backend os altera só por eventos
          const { rol: _rol, situacao: _situacao, oficio: _oficio, ...cadastro } = dados
          const atualizado = await membrosApi.atualizar(membro.id, cadastro)
          navegar('/membros', { replace: true, state: { aviso: `Dados de ${atualizado.nome} atualizados.` } })
        }}
      />

      {podeExcluirMembro(usuario) && (
        <section className="zona-perigo" aria-labelledby="zona-perigo-titulo">
          <h2 id="zona-perigo-titulo">Excluir membro</h2>
          <p>
            Use para cadastros feitos por engano. O membro deixa de aparecer no rol e nas buscas, mas o histórico e o
            registro de auditoria são preservados. Para quem saiu da igreja (transferência, falecimento ou exclusão
            disciplinar), registre o evento eclesiástico correspondente em vez de excluir.
          </p>
          <button type="button" className="botao perigo" onClick={() => setConfirmando(true)}>
            Excluir membro…
          </button>
        </section>
      )}

      <DialogoConfirmar
        aberto={confirmando}
        titulo="Excluir este membro?"
        rotuloConfirmar="Excluir membro"
        ocupado={excluindo}
        erro={erroExclusao}
        onConfirmar={excluir}
        onCancelar={() => {
          setConfirmando(false)
          setErroExclusao(null)
        }}
      >
        <p>
          <strong>{membro.nome}</strong> (nº {membro.numero_rol ?? '—'}) será removido(a) do rol. O número do rol ficará
          livre para outro cadastro, e a conta de usuário vinculada, se houver, será desvinculada.
        </p>
      </DialogoConfirmar>
    </section>
  )
}
