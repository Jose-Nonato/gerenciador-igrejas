import { useEffect, useState } from 'react'
import { ApiError } from './api/client'

interface Resultado<T> {
  chave: string
  dados?: T
  erro?: string
}

/**
 * Carrega dados da API sempre que `deps` mudam (ou `recarregar()` é chamado).
 * Enquanto a consulta da vez não termina, `carregando` é true e `dados` mantém o resultado anterior.
 */
export function useCarga<T>(buscar: () => Promise<T>, deps: readonly unknown[]) {
  const [versao, setVersao] = useState(0)
  const [resultado, setResultado] = useState<Resultado<T> | null>(null)
  const chave = JSON.stringify([...deps, versao])

  useEffect(() => {
    let ativo = true
    buscar()
      .then((dados) => ativo && setResultado({ chave, dados }))
      .catch(
        (err) =>
          ativo &&
          setResultado((r) => ({
            chave,
            dados: r?.dados,
            erro: err instanceof ApiError ? err.message : 'Falha ao carregar os dados.',
          })),
      )
    return () => {
      ativo = false
    }
    // `buscar` é recriada a cada render; quem decide recarregar é a `chave`
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave])

  return {
    dados: resultado?.dados,
    erro: resultado?.chave === chave ? resultado.erro : undefined,
    carregando: resultado?.chave !== chave,
    recarregar: () => setVersao((v) => v + 1),
  }
}
