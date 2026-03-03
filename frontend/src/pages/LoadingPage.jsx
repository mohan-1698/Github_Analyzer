import { motion } from 'framer-motion'
import { Github, Zap } from 'lucide-react'

export default function LoadingPage() {
  return (
    <div className="min-h-screen bg-gradient-animated flex flex-col items-center justify-center">
      {/* Animated logo */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mb-6"
      >
        <Github className="w-8 h-8 text-white" />
      </motion.div>

      {/* Loading text */}
      <h2 className="text-3xl font-bold mb-4 text-center">GitHub Analyzer</h2>

      {/* Animated spinner */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        className="w-12 h-12 border-4 border-slate-700 border-t-blue-500 rounded-full mb-6"
      />

      {/* Status text with animation */}
      <motion.div
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity }}
        className="text-slate-400 flex items-center gap-2"
      >
        <Zap className="w-4 h-4 text-yellow-400" />
        <span>Initializing your dashboard...</span>
      </motion.div>

      {/* Loading dots */}
      <div className="flex gap-2 mt-6">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            animate={{ scale: [1, 1.5, 1] }}
            transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.2 }}
            className="w-2 h-2 bg-blue-500 rounded-full"
          />
        ))}
      </div>
    </div>
  )
}
