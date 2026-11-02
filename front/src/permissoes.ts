import type { Usuario } from './api/types'

/** Espelha o backend: excluir membro é só de admin e pastor (GestorUser). */
export function podeExcluirMembro(usuario: Usuario | null): boolean {
  return usuario?.perfil === 'admin' || usuario?.perfil === 'pastor'
}
