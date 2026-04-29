/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { getMe, loginWithPassword } from '../lib/api'
import { clearTokens, getAccessToken } from '../lib/authStorage'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(getAccessToken()))

  const hydrateUser = useCallback(async () => {
    setLoading(true)
    const token = getAccessToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const me = await getMe()
      setUser(me)
    } catch {
      clearTokens()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const token = getAccessToken()
    if (!token) return

    let canceled = false
    ;(async () => {
      try {
        const me = await getMe()
        if (!canceled) setUser(me)
      } catch {
        if (!canceled) {
          clearTokens()
          setUser(null)
        }
      } finally {
        if (!canceled) setLoading(false)
      }
    })()

    return () => {
      canceled = true
    }
  }, [])

  const login = useCallback(async (username, password) => {
    await loginWithPassword(username, password)
    const me = await getMe()
    setUser(me)
    return me
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      logout,
      refreshMe: hydrateUser,
    }),
    [user, loading, login, logout, hydrateUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
