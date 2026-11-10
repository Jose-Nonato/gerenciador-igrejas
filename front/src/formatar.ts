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

/** Data de hoje no fuso local ('AAAA-MM-DD'). `toISOString` usaria UTC e, à noite no Brasil, já daria amanhã. */
export function hojeLocal(): string {
  const d = new Date()
  const dois = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${dois(d.getMonth() + 1)}-${dois(d.getDate())}`
}
