import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { familiasApi } from '../api/endpoints'
import type { EstadoCivil, Familia, Membro, NovoMembro, Oficio, Rol, Sexo, SituacaoMembro } from '../api/types'
import { ESTADO_CIVIL, OFICIO, ROL, SEXO, SITUACAO } from '../rotulos'
import { Campo } from './Campo'
import { CampoSelect } from './CampoSelect'

const NOVA_FAMILIA = '__nova'

interface Formulario {
  nome: string
  rol: Rol
  numeroRol: string
  dataNascimento: string
  sexo: Sexo | ''
  estadoCivil: EstadoCivil | ''
  telefone: string
  email: string
  endereco: string
  familia: string
  nomeNovaFamilia: string
  situacao: SituacaoMembro
  oficio: Oficio
}

function inicial(m?: Membro): Formulario {
  return {
    nome: m?.nome ?? '',
    rol: m?.rol ?? 'NC',
    numeroRol: m?.numero_rol != null ? String(m.numero_rol) : '',
    dataNascimento: m?.data_nascimento ?? '',
    sexo: m?.sexo ?? '',
    estadoCivil: m?.estado_civil ?? '',
    telefone: m?.telefone ?? '',
    email: m?.email ?? '',
    endereco: m?.endereco ?? '',
    familia: m?.familia_id ?? '',
    nomeNovaFamilia: '',
    situacao: m?.situacao ?? 'ativo',
    oficio: m?.oficio ?? 'nenhum',
  }
}

const vazioParaNulo = (v: string) => (v.trim() === '' ? null : v.trim())
const hoje = () => new Date().toISOString().slice(0, 10)

interface Props {
  /** Presente = edição; rol, situação e ofício ficam bloqueados (mudam por eventos eclesiásticos) */
  membro?: Membro
  rotuloSalvar: string
  onSalvar: (dados: NovoMembro) => Promise<void>
}

export function MembroForm({ membro, rotuloSalvar, onSalvar }: Props) {
  const editando = membro !== undefined
  const [f, setF] = useState<Formulario>(() => inicial(membro))
  const [familias, setFamilias] = useState<Familia[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  // Se o membro falhar depois de a família ser criada, a nova tentativa reaproveita a família
  const familiaCriada = useRef<Familia | null>(null)

  useEffect(() => {
    let ativo = true
    familiasApi
      .listar()
      .then((lista) => ativo && setFamilias(lista))
      .catch(() => {
        // sem a lista o formulário continua usável, só sem escolher família
      })
    return () => {
      ativo = false
    }
  }, [])

  function mudar<K extends keyof Formulario>(campo: K, valor: Formulario[K]) {
    setF((atual) => ({ ...atual, [campo]: valor }))
  }

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!f.nome.trim()) return setErro('Informe o nome do membro.')
    if (f.numeroRol && !(Number(f.numeroRol) >= 1)) return setErro('O número do rol deve ser 1 ou maior.')
    if (f.dataNascimento > hoje()) return setErro('A data de nascimento não pode estar no futuro.')
    if (f.familia === NOVA_FAMILIA && !f.nomeNovaFamilia.trim()) return setErro('Informe o nome da nova família.')

    setErro(null)
    setEnviando(true)
    try {
      let familiaId: string | null = f.familia && f.familia !== NOVA_FAMILIA ? f.familia : null
      if (f.familia === NOVA_FAMILIA) {
        familiaCriada.current ??= await familiasApi.criar(f.nomeNovaFamilia.trim())
        familiaId = familiaCriada.current.id
      }
      await onSalvar({
        nome: f.nome.trim(),
        rol: f.rol,
        familia_id: familiaId,
        numero_rol: f.numeroRol ? Number(f.numeroRol) : null,
        data_nascimento: vazioParaNulo(f.dataNascimento),
        sexo: f.sexo || null,
        estado_civil: f.estadoCivil || null,
        telefone: vazioParaNulo(f.telefone),
        email: vazioParaNulo(f.email),
        endereco: vazioParaNulo(f.endereco),
        situacao: f.situacao,
        oficio: f.oficio,
      })
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar o membro.')
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={enviar} noValidate>
      <fieldset>
        <legend>Identificação</legend>
        <Campo
          rotulo="Nome completo *"
          value={f.nome}
          onChange={(e) => mudar('nome', e.target.value)}
          maxLength={255}
          required
          autoFocus
        />
        <div className="grade">
          <CampoSelect
            rotulo="Rol *"
            value={f.rol}
            onChange={(e) => mudar('rol', e.target.value as Rol)}
            disabled={editando}
            ajuda={editando ? 'Muda por evento eclesiástico (ex.: profissão de fé).' : undefined}
          >
            {Object.entries(ROL).map(([v, r]) => (
              <option key={v} value={v}>{r}</option>
            ))}
          </CampoSelect>
          <Campo
            rotulo="Número no rol"
            type="number"
            min={1}
            value={f.numeroRol}
            onChange={(e) => mudar('numeroRol', e.target.value)}
            ajuda={editando ? undefined : 'Em branco: o próximo número é atribuído automaticamente.'}
          />
        </div>
        <div className="grade">
          <Campo
            rotulo="Data de nascimento"
            type="date"
            max={hoje()}
            value={f.dataNascimento}
            onChange={(e) => mudar('dataNascimento', e.target.value)}
          />
          <CampoSelect rotulo="Sexo" value={f.sexo} onChange={(e) => mudar('sexo', e.target.value as Sexo | '')}>
            <option value="">Não informado</option>
            {Object.entries(SEXO).map(([v, r]) => (
              <option key={v} value={v}>{r}</option>
            ))}
          </CampoSelect>
          <CampoSelect
            rotulo="Estado civil"
            value={f.estadoCivil}
            onChange={(e) => mudar('estadoCivil', e.target.value as EstadoCivil | '')}
          >
            <option value="">Não informado</option>
            {Object.entries(ESTADO_CIVIL).map(([v, r]) => (
              <option key={v} value={v}>{r}</option>
            ))}
          </CampoSelect>
        </div>
      </fieldset>

      <fieldset>
        <legend>Contato e família</legend>
        <div className="grade">
          <Campo
            rotulo="Telefone"
            type="tel"
            autoComplete="off"
            maxLength={32}
            value={f.telefone}
            onChange={(e) => mudar('telefone', e.target.value)}
          />
          <Campo
            rotulo="E-mail"
            type="email"
            autoComplete="off"
            value={f.email}
            onChange={(e) => mudar('email', e.target.value)}
          />
        </div>
        <Campo rotulo="Endereço" value={f.endereco} onChange={(e) => mudar('endereco', e.target.value)} />
        <CampoSelect rotulo="Família" value={f.familia} onChange={(e) => mudar('familia', e.target.value)}>
          <option value="">Sem família</option>
          {familias.map((fam) => (
            <option key={fam.id} value={fam.id}>{fam.nome}</option>
          ))}
          <option value={NOVA_FAMILIA}>+ Criar nova família…</option>
        </CampoSelect>
        {f.familia === NOVA_FAMILIA && (
          <Campo
            rotulo="Nome da nova família"
            value={f.nomeNovaFamilia}
            onChange={(e) => mudar('nomeNovaFamilia', e.target.value)}
            maxLength={255}
          />
        )}
      </fieldset>

      <fieldset>
        <legend>Situação atual</legend>
        <p className="ajuda">
          {editando ? (
            <>
              Rol, situação e ofício mudam por eventos eclesiásticos (profissão de fé, disciplina, ordenação, saída…).{' '}
              <Link to={`/membros/${membro.id}`}>Abrir a ficha para registrar um evento</Link>.
            </>
          ) : (
            'Normalmente ativo e sem ofício. Altere só ao cadastrar quem já tem outra situação; depois disso, mudanças passam por eventos eclesiásticos.'
          )}
        </p>
        <div className="grade">
          <CampoSelect
            rotulo="Situação"
            value={f.situacao}
            onChange={(e) => mudar('situacao', e.target.value as SituacaoMembro)}
            disabled={editando}
          >
            {Object.entries(SITUACAO).map(([v, r]) => (
              <option key={v} value={v}>{r}</option>
            ))}
          </CampoSelect>
          <CampoSelect
            rotulo="Ofício"
            value={f.oficio}
            onChange={(e) => mudar('oficio', e.target.value as Oficio)}
            disabled={editando}
          >
            {Object.entries(OFICIO).map(([v, r]) => (
              <option key={v} value={v}>{v === 'nenhum' ? 'Nenhum' : r}</option>
            ))}
          </CampoSelect>
        </div>
      </fieldset>

      {erro && <p className="aviso erro" role="alert">{erro}</p>}
      <div className="acoes-form">
        <button type="submit" className="botao" disabled={enviando}>
          {enviando ? 'Salvando…' : rotuloSalvar}
        </button>
        <Link to="/membros" className="botao secundario">Cancelar</Link>
      </div>
    </form>
  )
}
