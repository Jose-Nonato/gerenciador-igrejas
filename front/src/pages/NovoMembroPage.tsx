import { Link, useNavigate } from 'react-router-dom'
import { membrosApi } from '../api/endpoints'
import { MembroForm } from '../components/MembroForm'

export function NovoMembroPage() {
  const navegar = useNavigate()

  return (
    <section className="pagina estreita-media">
      <p className="migalha">
        <Link to="/membros">← Rol de membros</Link>
      </p>
      <h1>Adicionar membro</h1>
      <p className="subtitulo">Só o nome e o rol são obrigatórios; o restante pode ser completado depois.</p>
      <MembroForm
        rotuloSalvar="Salvar membro"
        onSalvar={async (dados) => {
          const criado = await membrosApi.criar(dados)
          navegar('/membros', { replace: true, state: { aviso: `${criado.nome} foi adicionado(a) ao rol.` } })
        }}
      />
    </section>
  )
}
