import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authService } from '../services/authService'
import { setAccessToken } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)

  const refreshUser = useCallback(async () => {
    setUser(await authService.me())
  }, [])

  useEffect(() => {
    let cancelled = false
    authService.me()
      .then((u) => { if (!cancelled) setUser(u) })
      .catch(() => { if (!cancelled) { setAccessToken(null); setUser(null) } })
      .finally(() => { if (!cancelled) setChecking(false) })
    const expired = () => { setAccessToken(null); setUser(null) }
    window.addEventListener('stocklens:unauthorized', expired)
    return () => { cancelled = true; window.removeEventListener('stocklens:unauthorized', expired) }
  }, [])

  const value = useMemo(() => ({
    user,
    checking,
    refreshUser,
    login: async (email, password) => setUser(await authService.login(email, password)),
    register: async (name, email, password) => setUser(await authService.register(name, email, password)),
    forgotPassword: (email) => authService.forgotPassword(email),
    resetPassword: (token, password) => authService.resetPassword(token, password),
    updateProfile: async (data) => setUser(await authService.updateProfile(data)),
    changePassword: (current, next) => authService.changePassword(current, next),
    logout: async () => {
      try { await authService.logout() } finally { setAccessToken(null); setUser(null) }
    },
  }), [user, checking, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
