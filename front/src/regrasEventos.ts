import type { Membro, TipoEvento } from './api/types'

/**
 * Orientação para a interface, espelhando back/controllers/regras_rol.py.
 * O backend é a fonte da verdade e recusa o que for inválido; aqui só se evita
 * oferecer ao usuário eventos que certamente seriam recusados.
 */
export function eventosPermitidos(m: Membro): TipoEvento[] {
  if (m.situacao === 'falecido') return []
  // Quem está fora do rol só pode ser recebido novamente
  if (m.situacao === 'transferido' || m.situacao === 'excluido') return ['recepcao']

  const tipos: TipoEvento[] = ['batismo', 'profissao_fe', 'recepcao']
  if (m.situacao === 'ativo' && m.rol === 'C') tipos.push('ordenacao')
  if (m.situacao === 'ativo') tipos.push('disciplina')
  if (m.situacao === 'em_disciplina') tipos.push('restauracao')
  tipos.push('saida')
  return tipos
}

/** Só o batismo dispensa a ata do Conselho. */
export const exigeAta = (tipo: TipoEvento): boolean => tipo !== 'batismo'

export const EFEITO_EVENTO: Record<TipoEvento, string> = {
  batismo: 'Apenas registra o batismo; não altera o rol do membro.',
  profissao_fe: 'O membro passa a ser comungante.',
  recepcao: 'O membro passa a ser comungante e volta à situação ativa.',
  ordenacao: 'Confere o ofício de presbítero ou diácono (só comungantes ativos).',
  disciplina: 'O membro passa a ficar em disciplina (só membros ativos).',
  restauracao: 'O membro em disciplina volta à situação ativa.',
  saida: 'O membro passa a transferido, falecido ou excluído. Falecido encerra o histórico.',
}
