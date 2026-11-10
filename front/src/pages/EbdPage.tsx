import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { ebdApi } from '../api/endpoints'
import { Campo } from '../components/Campo'
import { Carregando } from '../components/Carregando'
import { Dialogo } from '../components/Dialogo'
import { useAcessoEbd } from '../useAcessoEbd'
import { useCarga } from '../useCarga'

function NovaClasseDialogo({ onCriada, onFechar }: { onCriada: () => void; onFechar: () => void }) {
  const [nome, setNome] = useState('')
  const [faixa, setFaixa] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!nome.trim()) return setErro('Informe o nome da classe.')
    setErro(null)
    setEnviando(true)
    try {
      await ebdApi.criar({ nome: nome.trim(), faixa_etaria: faixa.trim() || null })
      onCriada()
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível criar a classe.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Nova classe" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <Campo rotulo="Nome *" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={100} autoFocus />
        <Campo
          rotulo="Faixa etária (opcional)"
          value={faixa}
          onChange={(e) => setFaixa(e.target.value)}
          maxLength={100}
          ajuda="Ex.: Adolescentes, 12 a 17 anos."
        />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
            {enviando ? 'Criando…' : 'Criar classe'}
          </button>
          <button type="button" className="botao secundario" onClick={onFechar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    </Dialogo>
  )
}

export function EbdPage() {
  const { gestor } = useAcessoEbd()
  const { dados: classes, erro, recarregar } = useCarga(() => ebdApi.listar(), [])
  const [criando, setCriando] = useState(false)

  if (erro && !classes) return <p className="aviso erro" role="alert">{erro}</p>
  if (!classes) return <Carregando />

  return (
    <section className="pagina">
      <div className="titulo-linha">
        <h1>{gestor ? 'Escola Bíblica Dominical' : 'Minha classe da EBD'}</h1>
        {gestor && (
          <button type="button" className="botao" onClick={() => setCriando(true)}>
            Nova classe
          </button>
        )}
      </div>

      {classes.length === 0 ? (
        <p className="vazio-texto">
          {gestor
            ? 'Nenhuma classe criada ainda. Comece criando a primeira.'
            : 'Você não é professor(a) de nenhuma classe.'}
        </p>
      ) : (
        <div className="atalhos">
          {classes.map((c) => (
            <Link key={c.id} to={`/ebd/${c.id}`} className="atalho">
              <strong>
                {c.nome}
                {!c.ativa && <span className="selo selo-imagem">Desativada</span>}
              </strong>
              <span>{c.faixa_etaria ?? 'Sem faixa etária'}</span>
              <span>
                {c.total_alunos} {c.total_alunos === 1 ? 'aluno' : 'alunos'} · {c.total_professores}{' '}
                {c.total_professores === 1 ? 'professor' : 'professores'}
              </span>
            </Link>
          ))}
        </div>
      )}

      {criando && (
        <NovaClasseDialogo
          onFechar={() => setCriando(false)}
          onCriada={() => {
            setCriando(false)
            recarregar()
          }}
        />
      )}
    </section>
  )
}
