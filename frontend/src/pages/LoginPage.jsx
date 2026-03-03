import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Github, Zap, BarChart3, Lightbulb } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { GITHUB_CLIENT_ID, GITHUB_REDIRECT_URI } from '../utils/constants'

export default function LoginPage({ setIsAuthenticated }) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()
  const callbackProcessed = useRef(false)

  useEffect(() => {
    // Handle OAuth callback - prevent React Strict Mode from calling twice
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    
    if (code && !callbackProcessed.current) {
      callbackProcessed.current = true
      handleCallback(code, state)
    }
  }, [searchParams])

  const handleCallback = async (code, state) => {
    try {
      const params = new URLSearchParams({
        code,
        ...(state && { state })
      })
      const response = await fetch(
        `http://localhost:8000/auth/github/callback?${params.toString()}`,
        {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        }
      )
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error('Auth failed:', response.status, errorData)
        // Reset the flag to allow retry
        callbackProcessed.current = false
        return
      }
      
      const data = await response.json()

      if (data.access_token && data.session_id) {
        console.log('🔐 OAuth Callback Response:')
        console.log('   access_token:', data.access_token.substring(0, 50) + '...')
        console.log('   session_id:', data.session_id)
        console.log('   user:', data.user)
        
        login(data.access_token, data.session_id)
        
        console.log('💾 Stored in localStorage:')
        console.log('   access_token:', localStorage.getItem('access_token')?.substring(0, 50) + '...')
        console.log('   session_id:', localStorage.getItem('session_id'))
        
        setIsAuthenticated(true)
        navigate('/dashboard')
      } else {
        console.error('❌ Missing tokens in response:', data)
      }
    } catch (error) {
      console.error('Auth error:', error)
      // Reset the flag to allow retry
      callbackProcessed.current = false
    }
  }

  const handleGitHubLogin = async () => {
    try {
      // Call backend to get auth URL with state token
      const response = await fetch('http://localhost:8000/auth/github')
      const data = await response.json()
      
      if (data.auth_url) {
        // Redirect to GitHub with state token included
        window.location.href = data.auth_url
      }
    } catch (error) {
      console.error('GitHub auth error:', error)
    }
  }

  const features = [
    {
      icon: BarChart3,
      title: 'Advanced Analytics',
      description: 'Track your commits, contributions, and productivity metrics',
    },
    {
      icon: Lightbulb,
      title: 'AI-Powered Insights',
      description: 'Get intelligent recommendations powered by Google Gemini',
    },
    {
      icon: Zap,
      title: 'Real-time Updates',
      description: 'Live synchronization with your GitHub profile',
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-animated flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Animated background particles */}
      <div className="absolute inset-0 pointer-events-none">
        {[1, 2, 3].map((i) => (
          <motion.div
            key={i}
            animate={{
              x: [0, Math.sin(i * 45) * 100, 0],
              y: [0, Math.cos(i * 45) * 100, 0],
            }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            className={`absolute w-${32 + i * 20} h-${32 + i * 20} rounded-full opacity-10`}
            style={{
              background: `radial-gradient(circle, rgba(59, 130, 246, 0.5), transparent)`,
              top: `${i * 30}%`,
              left: `${i * 30}%`,
              filter: 'blur(40px)',
            }}
          />
        ))}
      </div>

      {/* Content */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="relative z-10 max-w-2xl w-full"
      >
        {/* Logo */}
        <motion.div className="text-center mb-12">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6"
          >
            <Github className="w-8 h-8 text-white" />
          </motion.div>

          <h1 className="text-5xl md:text-6xl font-bold mb-4 text-gradient">
            GitHub Analyzer
          </h1>
          <p className="text-xl text-slate-300">
            Discover insights into your development journey
          </p>
        </motion.div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="glass-hover p-6 rounded-lg text-center group"
            >
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 2, delay: index * 0.2, repeat: Infinity }}
                className={`w-12 h-12 rounded-lg flex items-center justify-center mx-auto mb-4 bg-gradient-to-br from-blue-500 to-purple-600 group-hover:shadow-lg group-hover:shadow-blue-500/50 transition-all`}
              >
                <feature.icon className="w-6 h-6 text-white" />
              </motion.div>
              <h3 className="font-bold mb-2">{feature.title}</h3>
              <p className="text-sm text-slate-400">{feature.description}</p>
            </motion.div>
          ))}
        </div>

        {/* Login Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="glass-hover p-8 md:p-12 rounded-2xl text-center relative overflow-hidden"
        >
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-blue-500/20 rounded-full blur-3xl" />
          <div className="relative z-10">
            <p className="text-slate-400 mb-6">
              Sign in with your GitHub account to get started
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleGitHubLogin}
              className="btn-primary mx-auto flex items-center gap-3 px-8"
            >
              <Github className="w-5 h-5" />
              Continue with GitHub
            </motion.button>

            <p className="text-xs text-slate-500 mt-6">
              We never store your personal information. Only basic profile data is used.
            </p>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
