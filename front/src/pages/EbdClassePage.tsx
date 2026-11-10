import { useState, type FormEvent } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { ebdApi } from '../api/endpoints'
import type { EbdClasse } from '../api/types'
import { Campo } from '../components/Campo'
import { Carregando } from '../components/Carregando'
import { Dialogo } from '../components/Dialogo'
import { EbdAlunosTab } from '../components/EbdAlunosTab'
import { EbdAulasTab } from '../components/EbdAulasTab'
import { EbdFrequenciaTab } from '../components/EbdFrequenciaTab'
import { EbdProfessoresTab } from '../components/EbdProfessoresTab'
import { useAcessoEbd } from '../useAcessoEbd'
import { useCarga } from '../useCarga'

const ABAS = [
  { id: 'alunos', rotulo: 'Alunos' },
  { id: 'professores', rotulo: 'Professores' },
  { id: 'aulas', rotulo: 'Aulas' },
  { id: 'frequencia', rotulo: 'Frequência' },
] as const

type AbaId = (typeof ABAS)[number]['id']

function EditarClasseDialogo({
  classe,
  onSalva,
  onFechar,
}: {
  classe: EbdClasse
  onSalva: () => void
  onFechar: () => void
}) {
  const [nome, setNome] = useState(classe.nome)
  const [faixa, setFaixa] = useState(classe.faixa_etaria ?? '')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!nome.trim()) return setErro('Informe o nome da classe.')
    setErro(null)
    setEnviando(true)
    try {
      await ebdApi.atualizar(classe.id, { nome: nome.trim(), faixa_etaria: faixa.trim() || null })
      onSalva()
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar a classe.')
      setEnviando(false)
    }
  }

  return (
    <Dialogo titulo="Editar classe" onFechar={onFechar}>
      <form onSubmit={enviar} noValidate>
        <Campo rotulo="Nome *" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={100} autoFocus />
        <Campo rotulo="Faixa etária (opcional)" value={faixa} onChange={(e) => setFaixa(e.target.value)} maxLength={100} />
        {erro && <p className="aviso erro" role="alert">{erro}</p>}
        <div className="acoes-form">
          <button type="submit" className="botao" disabled={enviando}>
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

export function EbdClassePage() {
  const { id = '' } = useParams<{ id: string }>()
  const [params, setParams] = useSearchParams()
  const { gestor } = useAcessoEbd()
  // A aba vai na URL: voltar de uma aula cai de novo em "Aulas"
  const aba: AbaId = ABAS.find((a) => a.id === params.get('aba'))?.id ?? 'alunos'
  const { dados: classe, erro, recarregar } = useCarga(() => ebdApi.obter(id), [id])
  const [editando, setEditando] = useState(false)
  const [erroAcao, setErroAcao] = useState<string | null>(null)

  async function alternarAtiva() {
    if (!classe) return
    setErroAcao(null)
    try {
      await ebdApi.atualizar(classe.id, { ativa: !classe.ativa })
      recarregar()
    } catch (err) {
      setErroAcao(err instanceof ApiError ? err.message : 'Não foi possível alterar a classe.')
    }
  }

  if (erro && !classe) {
    return (
      <section className="pagina">
        <p className="aviso erro" role="alert">{erro}</p>
        <Link to="/ebd">← EBD</Link>
      </section>
    )
  }
  if (!classe) return <Carregando />

  return (
    <section className="pagina">
      <p className="migalha">
        <Link to="/ebd">← EBD</Link>
      </p>
      <div className="titulo-linha">
        <h1>
          {classe.nome}
          {!classe.ativa && <span className="selo selo-imagem">Desativada</span>}
        </h1>
        {gestor && (
          <div className="acoes">
            <button type="button" className="botao secundario" onClick={() => setEditando(true)}>
              Editar classe
            </button>
            <button type="button" className="botao secundario" onClick={alternarAtiva}>
              {classe.ativa ? 'Desativar' : 'Reativar'}
            </button>
          </div>
        )}
      </div>
      <p className="subtitulo">
        {classe.faixa_etaria ?? 'Sem faixa etária'} · {classe.total_alunos}{' '}
        {classe.total_alunos === 1 ? 'aluno' : 'alunos'} · {classe.total_professores}{' '}
        {classe.total_professores === 1 ? 'professor' : 'professores'}
      </p>
      {!classe.ativa && (
        <p className="aviso atencao" role="status">
          Classe desativada: o histórico continua aqui, mas ela não recebe alunos, aulas nem presença até ser reativada.
        </p>
      )}
      {erroAcao && <p className="aviso erro" role="alert">{erroAcao}</p>}

      <div className="abas" role="tablist" aria-label="Seções da classe">
        {ABAS.map((a) => (
          <button
            key={a.id}
            type="button"
            role="tab"
            id={`aba-${a.id}`}
            aria-selected={aba === a.id}
            aria-controls={`painel-${a.id}`}
            className={aba === a.id ? 'aba ativa' : 'aba'}
            onClick={() => setParams({ aba: a.id }, { replace: true })}
          >
            {a.rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="painel">
        {aba === 'alunos' && <EbdAlunosTab classeId={id} ativa={classe.ativa} onMudou={recarregar} />}
        {aba === 'professores' && <EbdProfessoresTab classeId={id} ativa={classe.ativa} gestor={gestor} onMudou={recarregar} />}
        {aba === 'aulas' && <EbdAulasTab classeId={id} ativa={classe.ativa} />}
        {aba === 'frequencia' && <EbdFrequenciaTab classeId={id} />}
      </div>

      {editando && (
        <EditarClasseDialogo
          classe={classe}
          onFechar={() => setEditando(false)}
          onSalva={() => {
            setEditando(false)
            recarregar()
          }}
        />
      )}
    </section>
  )
}
