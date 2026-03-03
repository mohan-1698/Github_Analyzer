export const GITHUB_CLIENT_ID = import.meta.env.VITE_GITHUB_CLIENT_ID || 'your_client_id'
export const GITHUB_REDIRECT_URI = import.meta.env.VITE_GITHUB_REDIRECT_URI || 'http://localhost:3000/login'

export const ANIMATION_DURATION = {
  FAST: 0.3,
  NORMAL: 0.5,
  SLOW: 0.8,
}

export const COLORS = {
  PRIMARY: '#0f172a',
  SECONDARY: '#1e293b',
  ACCENT: '#3b82f6',
  SUCCESS: '#10b981',
  WARNING: '#f59e0b',
  DANGER: '#ef4444',
}

export const METRICS = {
  EXCELLENT: 85,
  GOOD: 70,
  AVERAGE: 50,
  POOR: 25,
}
