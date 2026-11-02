import { sociedadesApi } from './api/endpoints'
import { useAuth } from './auth/useAuth'
import { gerenciaSociedades } from './permissoes'
import { useCarga } from './useCarga'

/**
 * O que o usuário pode fazer com as sociedades internas:
 * - gestor (admin e pastor): vê todas, cria e altera diretoria;
 * - líder (mandato em exercício na diretoria): vê e edita só a sua, sem mexer na diretoria;
 * - os demais: nada.
 * O backend é quem decide; a lista de `/sociedades` já vem filtrada por esse critério.
 */
export function useAcessoSociedades() {
  const { usuario } = useAuth()
  const gestor = gerenciaSociedades(usuario)
  // O gestor sempre tem acesso: não precisa consultar a lista só para decidir o menu
  const { dados } = useCarga(
    () => (gestor ? Promise.resolve([]) : sociedadesApi.listar().catch(() => [])),
    [usuario?.id, gestor],
  )
  return {
    gestor,
    /** undefined enquanto carrega */
    temAcesso: gestor ? true : dados === undefined ? undefined : dados.length > 0,
    /** Ver a ficha completa do membro exige acesso ao rol (admin, pastor ou presbítero) */
    verFichas: usuario !== null && usuario.perfil !== 'usuario',
  }
}
