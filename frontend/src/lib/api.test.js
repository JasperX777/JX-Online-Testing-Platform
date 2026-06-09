import { expect, test, vi } from 'vitest'

import { api, loginWithPassword } from './api'
import { getAccessToken, getRefreshToken, setTokens } from './authStorage'

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

test('login stores access and refresh tokens', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ access: 'access-1', refresh: 'refresh-1' })))

  await loginWithPassword('jasper', 'secret')

  expect(getAccessToken()).toBe('access-1')
  expect(getRefreshToken()).toBe('refresh-1')
})

test('refreshes an expired access token and retries once', async () => {
  setTokens({ access: 'expired', refresh: 'refresh-1' })
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
    .mockResolvedValueOnce(jsonResponse({ access: 'fresh' }))
    .mockResolvedValueOnce(jsonResponse({ id: 7, username: 'jasper' }))
  vi.stubGlobal('fetch', fetchMock)

  const result = await api.get('/api/auth/me/')

  expect(result.username).toBe('jasper')
  expect(getAccessToken()).toBe('fresh')
  expect(fetchMock).toHaveBeenCalledTimes(3)
})

test('surfaces structured API validation errors', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ scheduled_for: ['Must be in the future.'] }, 400)))

  await expect(api.post('/api/execution-schedules/', {})).rejects.toThrow('scheduled_for')
})
