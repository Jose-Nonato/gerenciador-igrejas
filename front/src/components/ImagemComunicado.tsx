import { useEffect, useState } from 'react'
import { comunicadosApi } from '../api/endpoints'

interface Props {
  id: string
  titulo: string
  /** Muda quando a imagem é trocada, para recarregar */
  versao?: string
}

/** Mostra a imagem de um comunicado. Se não carregar, some sem atrapalhar o texto. */
export function ImagemComunicado({ id, titulo, versao }: Props) {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    let ativo = true
    let criada: string | null = null
    comunicadosApi
      .imagem(id)
      .then((blob) => {
        if (!ativo) return
        criada = URL.createObjectURL(blob)
        setUrl(criada)
      })
      .catch(() => ativo && setUrl(null))
    return () => {
      ativo = false
      if (criada) URL.revokeObjectURL(criada)
    }
  }, [id, versao])

  if (!url) return null
  return <img className="comunicado-imagem" src={url} alt={`Imagem do comunicado "${titulo}"`} />
}
