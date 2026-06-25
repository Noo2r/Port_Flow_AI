import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi, saveTokens, clearTokens } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
  })
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState(null)

  const login = useCallback(async (email, password) => {
    setLoading(true)
    setError(null)
    try {
      // Try JSON login first, fall back to form login
      let data
      try {
        data = await authApi.login(email, password)
      } catch {
        data = await authApi.loginForm(email, password)
      }
      saveTokens(data)
      const me = await authApi.me()
      localStorage.setItem('user', JSON.stringify(me))
      setUser(me)
      return me
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const register = useCallback(async (fullName, email, password) => {
    setLoading(true)
    setError(null)
    try {
      await authApi.register({ full_name: fullName, email, password })
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try { await authApi.logout() } catch { /* ignore */ }
    clearTokens()
    setUser(null)
  }, [])

  // Re-hydrate user from token on mount (e.g. after page refresh)
  useEffect(() => {
    if (!localStorage.getItem('access_token')) return
    if (user) return
    authApi.me()
      .then(me => { localStorage.setItem('user', JSON.stringify(me)); setUser(me) })
      .catch(() => { clearTokens(); setUser(null) })
  }, [user])

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
