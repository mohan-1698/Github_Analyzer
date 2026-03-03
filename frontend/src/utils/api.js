import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  const sessionId = localStorage.getItem('session_id')
  
  if (token) {
    config.params = {
      ...config.params,
      access_token: token,
      session_id: sessionId,
    }
  }
  
  console.log(`📤 [${config.method?.toUpperCase()}] ${config.url}`, { token: token ? '✓ present' : '✗ missing', sessionId })
  
  return config
})

// Handle errors
api.interceptors.response.use(
  (response) => {
    console.log(`📥 [${response.status}] ${response.config.url}`, response.data)
    return response
  },
  (error) => {
    console.error(`❌ [${error.response?.status}] ${error.config?.url}`, error.response?.data || error.message)
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('session_id')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  getGitHubAuthUrl: () => api.get('/auth/github'),
  handleCallback: (code) => api.get('/auth/github/callback', { params: { code } }),
}

export const githubAPI = {
  syncData: () => api.post('/github/sync'),
}

export const analyticsAPI = {
  calculate: () => api.post('/analytics/calculate'),
}

export const insightsAPI = {
  generate: () => api.post('/insights/generate'),
}

export const dashboardAPI = {
  getDashboardData: () => api.get('/dashboard/data'),
}

export default api
