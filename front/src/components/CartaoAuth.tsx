import type { ReactNode } from 'react'

interface Props {
  titulo: string
  subtitulo?: string
  children: ReactNode
}

/** Moldura das telas públicas (login, recuperação e redefinição de senha). */
export function CartaoAuth({ titulo, subtitulo, children }: Props) {
  return (
    <main className="auth-pagina">
      <section className="auth-cartao">
        <p className="marca">Gerenciador de Igrejas</p>
        <h1>{titulo}</h1>
        {subtitulo && <p className="subtitulo">{subtitulo}</p>}
        {children}
      </section>
    </main>
  )
}
