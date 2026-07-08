export class ApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function parseErrorBody(response: Response): Promise<{ message: string; code?: string }> {
  try {
    const body = await response.json()
    return {
      message: body?.error?.message ?? body?.detail ?? response.statusText,
      code: body?.error?.code,
    }
  } catch {
    return { message: response.statusText }
  }
}

export async function apiFetch<T = unknown>(path: string, init: globalThis.RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`/api${path}`, { ...init, headers })

  if (!response.ok) {
    const { message, code } = await parseErrorBody(response)
    throw new ApiError(message, response.status, code)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
