function resolveBase() {
  const envBase = import.meta.env.VITE_API_BASE as string | undefined
  if (envBase && envBase.trim()) {
    return envBase.replace(/\/+$/, '')
  }

  if (typeof window === 'undefined') {
    return '/api'
  }

  const { protocol, hostname, port } = window.location
  const isLocalHost = hostname === 'localhost' || hostname === '127.0.0.1'

  // If UI is served locally on any port except 8000 (e.g. 5173/5174/8080),
  // call the backend directly so we don't depend on a dev proxy.
  if (isLocalHost && port && port !== '8000') {
    return `${protocol}//${hostname}:8000/api`
  }

  return '/api'
}

const BASE = resolveBase()

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),

  upload: async <T>(path: string, formData: FormData): Promise<T> => {
    const res = await fetch(`${BASE}${path}`, { method: 'POST', body: formData })
    if (!res.ok) {
      const body = await res.text()
      throw new Error(`${res.status}: ${body}`)
    }
    return res.json()
  },
}
