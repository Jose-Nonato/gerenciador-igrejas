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

/** Soma dias a uma data 'AAAA-MM-DD' (calendário local, sem passar por UTC). */
export function somarDias(iso: string, dias: number): string {
  const [a, m, d] = iso.split('-').map(Number)
  const data = new Date(a, m - 1, d + dias)
  const dois = (n: number) => String(n).padStart(2, '0')
  return `${data.getFullYear()}-${dois(data.getMonth() + 1)}-${dois(data.getDate())}`
}

/** Instante ISO -> 'HH:MM' no horário local. */
export function horaCurta(iso: string): string {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

/** Instante ISO -> 'terça-feira, 17/11' no horário local. */
export function diaPorExtenso(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: '2-digit' })
}
