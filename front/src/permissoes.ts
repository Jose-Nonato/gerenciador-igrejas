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

/** Espelha o backend: só pastor e presbíteros têm agenda de atendimentos (admin não é oficial). */
export function ehOficial(usuario: Usuario | null): boolean {
  return usuario?.perfil === 'pastor' || usuario?.perfil === 'presbitero'
}

/** A agenda é de quem pode pedir uma conversa (conta ligada a um membro) ou atender uma. */
export function temAgenda(usuario: Usuario | null): boolean {
  return usuario !== null && (usuario.membro_id !== null || ehOficial(usuario))
}
