import { motion } from 'framer-motion'
import { TrendingUp, Award, Flame, Target } from 'lucide-react'
import { useEffect, useState } from 'react'

export default function ScoreCard({ title, score = 0, label, icon: Icon = Target, color = 'blue' }) {
  const [displayScore, setDisplayScore] = useState(0)

  useEffect(() => {
    let interval
    const increment = score / 30

    interval = setInterval(() => {
      setDisplayScore((prev) => {
        const next = prev + increment
        return next > score ? score : next
      })
    }, 30)

    return () => clearInterval(interval)
  }, [score])

  const getColorClasses = (color) => {
    const colors = {
      blue: 'from-blue-500 to-blue-600',
      green: 'from-green-500 to-green-600',
      purple: 'from-purple-500 to-purple-600',
      orange: 'from-orange-500 to-orange-600',
    }
    return colors[color] || colors.blue
  }

  const getScoreLabel = (score) => {
    if (score >= 85) return 'Elite'
    if (score >= 70) return 'Good'
    if (score >= 50) return 'Average'
    return 'Improving'
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      whileHover={{ scale: 1.05, y: -5 }}
      className="glass-hover p-6 rounded-xl relative overflow-hidden group h-full"
    >
      {/* Animated background gradient */}
      <div className={`absolute inset-0 bg-gradient-to-br ${getColorClasses(color)} opacity-0 group-hover:opacity-10 transition-opacity duration-500`} />

      {/* Glow effect */}
      <div className={`absolute -top-10 -right-10 w-32 h-32 bg-gradient-to-br ${getColorClasses(color)} rounded-full blur-2xl opacity-0 group-hover:opacity-30 transition-opacity duration-500`} />

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-slate-400 text-sm mb-1">{title}</p>
            <h3 className="text-2xl font-bold">{label}</h3>
          </div>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            className={`p-3 rounded-lg bg-gradient-to-br ${getColorClasses(color)} text-white`}
          >
            <Icon className="w-6 h-6" />
          </motion.div>
        </div>

        {/* Score Display */}
        <div className="mb-4">
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-gradient">
              {Math.round(displayScore)}
            </span>
            <span className="text-slate-400">/100</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-700/50 rounded-full h-2 overflow-hidden mb-3">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${displayScore}%` }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
            className={`h-full bg-gradient-to-r ${getColorClasses(color)} shadow-lg`}
          />
        </div>

        {/* Status */}
        <div className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${
            score >= 85 ? 'bg-green-500' :
            score >= 70 ? 'bg-blue-500' :
            score >= 50 ? 'bg-yellow-500' :
            'bg-red-500'
          } animate-pulse`} />
          <span className="text-sm text-slate-400">
            {getScoreLabel(score)}
          </span>
        </div>
      </div>
    </motion.div>
  )
}
