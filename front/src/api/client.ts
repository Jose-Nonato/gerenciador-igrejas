import type { TokenPair } from './types'

const BASE_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
const STORAGE_KEY = 'gi.tokens'

type Tokens = Pick<TokenPair, 'access_token' | 'refresh_token'>

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// ---------- armazenamento dos tokens ----------

export function getTokens(): Tokens | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Tokens) : null
  } catch {
    return null
  }
}

export function setTokens(tokens: Tokens | null): void {
  try {
    if (tokens) localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // armazenamento indisponível: a sessão vale só até recarregar a página
  }
}

// Avisa o AuthContext quando a sessão não pode mais ser renovada
let onSessionExpired: () => void = () => {}
export function setSessionExpiredHandler(handler: () => void): void {
  onSessionExpired = handler
}

// ---------- requisições ----------

function mensagemDeErro(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  // Erro de validação do FastAPI (422): lista de {loc, msg}
  if (Array.isArray(detail) && detail.length > 0) {
    const msg = (detail[0] as { msg?: string }).msg ?? 'Dados inválidos'
    return msg.replace(/^Value error, /, '')
  }
  return status >= 500 ? 'Erro no servidor. Tente novamente.' : 'Não foi possível concluir a operação.'
}

// Uma única renovação por vez: o refresh token é de uso único no backend
let refreshing: Promise<boolean> | null = null

async function renovarTokens(): Promise<boolean> {
  const atual = getTokens()
  if (!atual) return false
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: atual.refresh_token }),
    })
    if (!res.ok) return false
    const novo = (await res.json()) as TokenPair
    setTokens({ access_token: novo.access_token, refresh_token: novo.refresh_token })
    return true
  } catch {
    return false
  }
}

function renovarUmaVez(): Promise<boolean> {
  refreshing ??= renovarTokens().finally(() => {
    refreshing = null
  })
  return refreshing
}

interface Opcoes {
  method?: string
  json?: unknown
  form?: Record<string, string>
  /** Upload de arquivo (multipart); o navegador define o Content-Type */
  arquivo?: FormData
  query?: Record<string, string | number | undefined>
  /** false = rota pública, sem Authorization nem tentativa de renovar */
  auth?: boolean
}

async function enviar(path: string, opcoes: Opcoes): Promise<Response> {
  const url = new URL(BASE_URL + path)
  for (const [k, v] of Object.entries(opcoes.query ?? {})) {
    if (v !== undefined && v !== '') url.searchParams.set(k, String(v))
  }
  const headers: Record<string, string> = {}
  let body: BodyInit | undefined
  if (opcoes.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opcoes.json)
  } else if (opcoes.arquivo) {
    body = opcoes.arquivo
  } else if (opcoes.form) {
    body = new URLSearchParams(opcoes.form)
  }
  const tokens = opcoes.auth === false ? null : getTokens()
  if (tokens) headers.Authorization = `Bearer ${tokens.access_token}`
  return fetch(url, { method: opcoes.method ?? 'GET', headers, body })
}

async function request(path: string, opcoes: Opcoes = {}): Promise<Response> {
  let res: Response
  try {
    res = await enviar(path, opcoes)
  } catch {
    throw new ApiError(0, 'Sem conexão com o servidor.')
  }

  if (res.status === 401 && opcoes.auth !== false && getTokens()) {
    if (await renovarUmaVez()) {
      res = await enviar(path, opcoes)
    } else {
      setTokens(null)
      onSessionExpired()
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, mensagemDeErro(body, res.status))
  }
  return res
}

export async function api<T>(path: string, opcoes: Opcoes = {}): Promise<T> {
  const res = await request(path, opcoes)
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

export async function apiBlob(path: string, opcoes: Opcoes = {}): Promise<Blob> {
  return (await request(path, opcoes)).blob()
}
