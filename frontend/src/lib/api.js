import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './authStorage'

async function refreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) {
    throw new Error('No refresh token available')
  }

  const response = await fetch('/api/auth/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })

  if (!response.ok) {
    clearTokens()
    throw new Error('Token refresh failed')
  }

  const payload = await response.json()
  setTokens({ access: payload.access })
  return payload.access
}

async function request(path, options = {}, retry = true) {
  const token = getAccessToken()
  const headers = { ...(options.headers ?? {}) }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] ?? 'application/json'
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(path, {
    ...options,
    headers,
  })

  if (response.status === 401 && retry && getRefreshToken()) {
    try {
      await refreshAccessToken()
      return request(path, options, false)
    } catch (error) {
      clearTokens()
      throw error
    }
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const payload = await response.json()
      detail = payload.detail || JSON.stringify(payload)
    } catch {
      // Ignore JSON parse errors and keep fallback text.
    }
    throw new Error(detail)
  }

  if (response.status === 204) return null

  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) return null
  return response.json()
}

export const api = {
  get: (path) => request(path, { method: 'GET' }),
  post: (path, data) => request(path, { method: 'POST', body: JSON.stringify(data) }),
  patch: (path, data) => request(path, { method: 'PATCH', body: JSON.stringify(data) }),
  put: (path, data) => request(path, { method: 'PUT', body: JSON.stringify(data) }),
  del: (path) => request(path, { method: 'DELETE' }),
}

export function registerUser({ username, email, password }) {
  return api.post('/api/auth/register/', { username, email, password })
}

export async function loginWithPassword(username, password) {
  const payload = await request(
    '/api/auth/token/',
    {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    },
    false,
  )

  setTokens({ access: payload.access, refresh: payload.refresh })
  return payload
}

export function getMe() {
  return api.get('/api/auth/me/')
}
