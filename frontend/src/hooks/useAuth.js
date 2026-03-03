import { useState, useCallback } from 'react'

export const useAuth = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return !!localStorage.getItem('access_token')
  })

  const login = useCallback((accessToken, sessionId) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('session_id', sessionId)
    setIsLoggedIn(true)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('session_id')
    setIsLoggedIn(false)
  }, [])

  const getAccessToken = useCallback(() => {
    return localStorage.getItem('access_token')
  }, [])

  const getSessionId = useCallback(() => {
    return localStorage.getItem('session_id')
  }, [])

  return {
    isLoggedIn,
    login,
    logout,
    getAccessToken,
    getSessionId,
  }
}
