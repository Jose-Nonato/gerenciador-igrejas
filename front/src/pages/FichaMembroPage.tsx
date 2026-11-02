import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { membrosApi } from '../api/endpoints'
import type { Evento, Membro, NovoEvento } from '../api/types'
import { Carregando } from '../components/Carregando'
import { EventoForm } from '../components/EventoForm'
import { formatarData } from '../formatar'
import { eventosPermitidos } from '../regrasEventos'
import { ESTADO_CIVIL, FORMA_RECEPCAO, OFICIO, ROL, SEXO, SITUACAO, TIPO_EVENTO } from '../rotulos'

function Dado({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="dado">
      <dt>{rotulo}</dt>
      <dd>{children || '—'}</dd>
    </div>
  )
}

function detalhesDoEvento(ev: Evento): string[] {
  const itens: string[] = []
  if (ev.forma_recepcao) itens.push(`Forma: ${FORMA_RECEPCAO[ev.forma_recepcao]}`)
  if (ev.oficio) itens.push(`Ofício: ${OFICIO[ev.oficio] === '—' ? 'Nenhum' : OFICIO[ev.oficio]}`)
  if (ev.situacao_resultante) itens.push(`Situação resultante: ${SITUACAO[ev.situacao_resultante]}`)
  if (ev.igreja_relacionada) itens.push(`Igreja: ${ev.igreja_relacionada}`)
  if (ev.ata_conselho) itens.push(`Ata: ${ev.ata_conselho}`)
  return itens
}

export function FichaMembroPage() {
  const { id } = useParams<{ id: string }>()
  const [membro, setMembro] = useState<Membro | null>(null)
  const [eventos, setEventos] = useState<Evento[]>([])
  const [erroCarga, setErroCarga] = useState<string | null>(null)
  const [registrando, setRegistrando] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let ativo = true
    Promise.all([membrosApi.obter(id), membrosApi.eventos(id)])
      .then(([m, evs]) => {
        if (!ativo) return
        setMembro(m)
        setEventos(evs)
      })
      .catch((err) => ativo && setErroCarga(err instanceof ApiError ? err.message : 'Falha ao carregar a ficha.'))
    return () => {
      ativo = false
    }
  }, [id])

  async function registrar(dados: NovoEvento) {
    if (!membro) return
    // O backend devolve o membro já com os efeitos do evento aplicados
    const { evento, membro: atualizado } = await membrosApi.registrarEvento(membro.id, dados)
    setMembro(atualizado)
    setEventos((atuais) => [...atuais, evento])
    setRegistrando(false)
    setAviso(`${TIPO_EVENTO[evento.tipo]} registrado(a).`)
  }

  if (erroCarga) {
    return (
      <section className="pagina">
        <p className="aviso erro" role="alert">{erroCarga}</p>
        <Link to="/membros">← Voltar ao rol</Link>
      </section>
    )
  }
  if (!membro) return <Carregando />

  const podeRegistrar = eventosPermitidos(membro).length > 0
  // Do mais recente para o mais antigo (o backend devolve em ordem cronológica)
  const linhaDoTempo = [...eventos].reverse()

  return (
    <section className="pagina estreita-media">
      <p className="migalha">
        <Link to="/membros">← Rol de membros</Link>
      </p>
      <div className="titulo-linha">
        <div>
          <h1>{membro.nome}</h1>
          <p className="subtitulo">
            Nº {membro.numero_rol ?? '—'} · {ROL[membro.rol]} · <span className={`selo ${membro.situacao}`}>{SITUACAO[membro.situacao]}</span>
            {membro.oficio !== 'nenhum' && <> · {OFICIO[membro.oficio]}</>}
          </p>
        </div>
        <Link to={`/membros/${membro.id}/editar`} className="botao secundario">Editar dados</Link>
      </div>

      {aviso && <p className="aviso sucesso" role="status">{aviso}</p>}

      <section aria-labelledby="titulo-dados" className="cartao">
        <h2 id="titulo-dados">Dados cadastrais</h2>
        <dl className="dados">
          <Dado rotulo="Nascimento">{formatarData(membro.data_nascimento) === '—' ? null : formatarData(membro.data_nascimento)}</Dado>
          <Dado rotulo="Sexo">{membro.sexo && SEXO[membro.sexo]}</Dado>
          <Dado rotulo="Estado civil">{membro.estado_civil && ESTADO_CIVIL[membro.estado_civil]}</Dado>
          <Dado rotulo="Telefone">{membro.telefone}</Dado>
          <Dado rotulo="E-mail">{membro.email}</Dado>
          <Dado rotulo="Endereço">{membro.endereco}</Dado>
        </dl>
      </section>

      <section aria-labelledby="titulo-historico" className="cartao">
        <div className="titulo-linha">
          <h2 id="titulo-historico">Histórico eclesiástico</h2>
          {!registrando && (
            <button
              type="button"
              className="botao"
              onClick={() => {
                setAviso(null)
                setRegistrando(true)
              }}
              disabled={!podeRegistrar}
              title={podeRegistrar ? undefined : 'Membro falecido não admite novos eventos'}
            >
              Registrar evento
            </button>
          )}
        </div>

        {!podeRegistrar && <p className="ajuda">Membro falecido: o histórico está encerrado.</p>}

        {registrando && (
          <EventoForm membro={membro} onRegistrar={registrar} onCancelar={() => setRegistrando(false)} />
        )}

        {linhaDoTempo.length === 0 ? (
          <p className="vazio-texto">Nenhum evento registrado.</p>
        ) : (
          <ol className="linha-do-tempo">
            {linhaDoTempo.map((ev) => (
              <li key={ev.id}>
                <div className="ev-topo">
                  <strong>{TIPO_EVENTO[ev.tipo]}</strong>
                  <time dateTime={ev.data}>{formatarData(ev.data)}</time>
                </div>
                {detalhesDoEvento(ev).length > 0 && <p className="ev-detalhes">{detalhesDoEvento(ev).join(' · ')}</p>}
                {ev.observacao && <p className="ev-obs">{ev.observacao}</p>}
              </li>
            ))}
          </ol>
        )}
      </section>
    </section>
  )
}
