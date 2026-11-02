/** 'AAAA-MM-DD' -> 'DD/MM/AAAA' (sem passar por Date, para não deslocar o dia por fuso). */
export function formatarData(iso: string | null): string {
  if (!iso) return '—'
  const [a, m, d] = iso.split('-')
  return `${d}/${m}/${a}`
}

/** Instante ISO (com fuso) -> 'DD/MM/AAAA HH:MM' no horário local. */
export function formatarDataHora(iso: string | null): string {
  if (!iso) return 'Nunca'
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}
