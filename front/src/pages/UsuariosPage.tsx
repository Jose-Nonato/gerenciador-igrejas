import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { membrosApi, usuariosApi } from '../api/endpoints'
import type { Usuario } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Carregando } from '../components/Carregando'
import { ConvidarUsuarioDialogo } from '../components/ConvidarUsuarioDialogo'
import { GerenciarUsuarioDialogo } from '../components/GerenciarUsuarioDialogo'
import { formatarDataHora } from '../formatar'
import { PERFIL, STATUS_USUARIO } from '../rotulos'

export function UsuariosPage() {
  const { usuario: eu } = useAuth()
  const ehAdmin = eu?.perfil === 'admin'
  const [usuarios, setUsuarios] = useState<Usuario[] | null>(null)
  const [nomes, setNomes] = useState<Record<string, string>>({})
  const [erro, setErro] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [convidando, setConvidando] = useState(false)
  const [editando, setEditando] = useState<Usuario | null>(null)

  useEffect(() => {
    let ativo = true
    usuariosApi
      .listar()
      .then(async (lista) => {
        if (!ativo) return
        setUsuarios(lista)
        // A API de usuários só traz o id do membro: busca o nome de quem tem vínculo
        const ids = [...new Set(lista.map((u) => u.membro_id).filter((id): id is string => id !== null))]
        const pares = await Promise.all(
          ids.map((id) =>
            membrosApi
              .obter(id)
              .then((m) => [id, m.nome] as const)
              .catch(() => null),
          ),
        )
        if (ativo) setNomes(Object.fromEntries(pares.filter((p) => p !== null)))
      })
      .catch((err) => ativo && setErro(err instanceof ApiError ? err.message : 'Falha ao carregar os usuários.'))
    return () => {
      ativo = false
    }
  }, [])

  if (erro) return <p className="aviso erro" role="alert">{erro}</p>
  if (!usuarios) return <Carregando />

  const ordenados = [...usuarios].sort((a, b) => a.email.localeCompare(b.email))

  return (
    <section className="pagina">
      <div className="titulo-linha">
        <h1>Usuários</h1>
        {ehAdmin && (
          <button
            type="button"
            className="botao"
            onClick={() => {
              setAviso(null)
              setConvidando(true)
            }}
          >
            Convidar usuário
          </button>
        )}
      </div>
      {!ehAdmin && <p className="subtitulo">Somente o administrador pode convidar e alterar usuários.</p>}
      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}

      <div className="tabela-wrap">
        <table>
          <thead>
            <tr>
              <th>E-mail</th>
              <th>Perfil</th>
              <th>Status</th>
              <th>Membro vinculado</th>
              <th>Último acesso</th>
              {ehAdmin && <th>Ações</th>}
            </tr>
          </thead>
          <tbody>
            {ordenados.map((u) => (
              <tr key={u.id}>
                <td>
                  {u.email}
                  {u.id === eu?.id && <span className="ajuda"> (você)</span>}
                </td>
                <td>{PERFIL[u.perfil]}</td>
                <td><span className={`selo status-${u.status}`}>{STATUS_USUARIO[u.status]}</span></td>
                <td>{u.membro_id ? (nomes[u.membro_id] ?? '…') : '—'}</td>
                <td>{formatarDataHora(u.ultimo_acesso)}</td>
                {ehAdmin && (
                  <td className="acoes">
                    <button
                      type="button"
                      className="botao secundario pequeno"
                      aria-label={`Gerenciar ${u.email}`}
                      onClick={() => {
                        setAviso(null)
                        setEditando(u)
                      }}
                    >
                      Gerenciar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {convidando && (
        <ConvidarUsuarioDialogo
          onFechar={() => setConvidando(false)}
          onConvidado={(novo) => {
            setUsuarios((atuais) => [...(atuais ?? []), novo])
            setConvidando(false)
            setAviso(`Convite enviado para ${novo.email}.`)
          }}
        />
      )}

      {editando && (
        <GerenciarUsuarioDialogo
          usuario={editando}
          ehProprio={editando.id === eu?.id}
          nomeMembro={editando.membro_id ? (nomes[editando.membro_id] ?? null) : null}
          onFechar={() => setEditando(null)}
          onSalvo={(atualizado, nomeMembro) => {
            setUsuarios((atuais) => (atuais ?? []).map((u) => (u.id === atualizado.id ? atualizado : u)))
            if (atualizado.membro_id && nomeMembro) {
              setNomes((atuais) => ({ ...atuais, [atualizado.membro_id as string]: nomeMembro }))
            }
            setEditando(null)
            setAviso(`Usuário ${atualizado.email} atualizado.`)
          }}
        />
      )}
    </section>
  )
}
