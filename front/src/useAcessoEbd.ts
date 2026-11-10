import { ebdApi } from './api/endpoints'
import { useAuth } from './auth/useAuth'
import { gerenciaEbd } from './permissoes'
import { useCarga } from './useCarga'

/**
 * O que o usuário pode fazer na EBD:
 * - gestor (admin e pastor): vê todas as classes, cria e define professores;
 * - professor (em exercício numa classe): vê e edita só a sua;
 * - os demais: nada.
 * O backend é quem decide; a lista de `/ebd/classes` já vem filtrada por esse critério.
 */
export function useAcessoEbd() {
  const { usuario } = useAuth()
  const gestor = gerenciaEbd(usuario)
  // O gestor sempre tem acesso: não precisa consultar a lista só para decidir o menu
  const { dados } = useCarga(
    () => (gestor ? Promise.resolve([]) : ebdApi.listar().catch(() => [])),
    [usuario?.id, gestor],
  )
  return {
    gestor,
    /** undefined enquanto carrega */
    temAcesso: gestor ? true : dados === undefined ? undefined : dados.length > 0,
  }
}
