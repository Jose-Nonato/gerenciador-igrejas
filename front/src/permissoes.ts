import type { Usuario } from './api/types'

/** Espelha o backend: excluir membro é só de admin e pastor (GestorUser). */
export function podeExcluirMembro(usuario: Usuario | null): boolean {
  return usuario?.perfil === 'admin' || usuario?.perfil === 'pastor'
}

/** Espelha o backend: as sociedades internas são só de admin e pastor (GestorUser). */
export function gerenciaSociedades(usuario: Usuario | null): boolean {
  return usuario?.perfil === 'admin' || usuario?.perfil === 'pastor'
}

/** Espelha o backend: criar classes e definir professores da EBD é só de admin e pastor (GestorUser). */
export function gerenciaEbd(usuario: Usuario | null): boolean {
  return usuario?.perfil === 'admin' || usuario?.perfil === 'pastor'
}
