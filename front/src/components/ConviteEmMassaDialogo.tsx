import { useState } from 'react'
import { ApiError } from '../api/client'
import { usuariosApi } from '../api/endpoints'
import { useCarga } from '../useCarga'
import { Carregando } from './Carregando'
import { Dialogo } from './Dialogo'

const POR_RODADA = 50

interface Props {
  /** Chamado ao fechar; `mudou` indica que contas foram criadas (a lista precisa recarregar) */
  onFechar: (mudou: boolean) => void
}

export function ConviteEmMassaDialogo({ onFechar }: Props) {
  // 1) simulação: só conta quem seria convidado
  const { dados: previa, erro: erroPrevia, recarregar } = useCarga(() => usuariosApi.convidarEmMassa(true), [])
  const [convidadosTotal, setConvidadosTotal] = useState(0)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function convidar() {
    setErro(null)
    setEnviando(true)
    try {
      const r = await usuariosApi.convidarEmMassa(false, POR_RODADA)
      setConvidadosTotal((n) => n + r.convidados)
      recarregar() // nova simulação: mostra quantos ainda faltam
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível enviar os convites.')
    } finally {
      setEnviando(false)
    }
  }

  const fechar = () => onFechar(convidadosTotal > 0)
  const nesta = previa ? Math.min(previa.elegiveis, POR_RODADA) : 0

  return (
    <Dialogo titulo="Convidar membros do rol" onFechar={fechar}>
      {erroPrevia && !previa && <p className="aviso erro" role="alert">{erroPrevia}</p>}
      {!previa && !erroPrevia && <Carregando />}

      {previa && (
        <>
          {convidadosTotal > 0 && (
            <p className="aviso sucesso" role="status">
              {convidadosTotal} {convidadosTotal === 1 ? 'convite enviado' : 'convites enviados'}.
            </p>
          )}

          {previa.elegiveis > 0 ? (
            <p className="dialogo-texto">
              <strong>{previa.elegiveis}</strong> {previa.elegiveis === 1 ? 'membro do rol tem' : 'membros do rol têm'}{' '}
              e-mail e ainda não {previa.elegiveis === 1 ? 'tem' : 'têm'} conta. Cada um receberá um e-mail com um link
              para criar a senha (perfil <em>Usuário</em>, o de menor acesso).
              {previa.elegiveis > POR_RODADA && ` Os convites saem em rodadas de ${POR_RODADA}.`}
            </p>
          ) : (
            <p className="dialogo-texto">Não há mais membros para convidar.</p>
          )}

          {(previa.sem_email > 0 || previa.email_em_uso > 0) && (
            <ul className="ajuda lista-simples">
              {previa.sem_email > 0 && <li>{previa.sem_email} sem e-mail cadastrado (não podem ser convidados em massa).</li>}
              {previa.email_em_uso > 0 && <li>{previa.email_em_uso} com e-mail já usado por outra conta.</li>}
            </ul>
          )}

          {erro && <p className="aviso erro" role="alert">{erro}</p>}
          <div className="acoes-form">
            {previa.elegiveis > 0 && (
              <button type="button" className="botao" onClick={convidar} disabled={enviando}>
                {enviando ? 'Enviando…' : `Convidar ${nesta} ${nesta === 1 ? 'membro' : 'membros'}`}
              </button>
            )}
            <button type="button" className="botao secundario" onClick={fechar} disabled={enviando}>
              {convidadosTotal > 0 || previa.elegiveis === 0 ? 'Fechar' : 'Cancelar'}
            </button>
          </div>
        </>
      )}
    </Dialogo>
  )
}
