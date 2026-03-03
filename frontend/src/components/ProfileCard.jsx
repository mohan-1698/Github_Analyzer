import { motion } from 'framer-motion'
import { Github, MapPin, Mail, LinkIcon } from 'lucide-react'

export default function ProfileCard({ user, stats = {} }) {
  if (!user) {
    return (
      <div className="glass p-8 rounded-2xl">
        <div className="skeleton h-40 rounded-lg" />
      </div>
    )
  }

  // Use real stats or defaults
  const totalCommits = stats.totalCommits || 0
  const totalRepos = stats.totalRepos || 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass-hover p-8 rounded-2xl overflow-hidden relative group"
    >
      {/* Background glow effect */}
      <div className="absolute -top-20 -right-20 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl group-hover:bg-blue-500/20 transition-all duration-500" />

      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center gap-6">
        {/* Avatar */}
        <motion.div
          whileHover={{ scale: 1.1 }}
          className="relative"
        >
          <img
            src={user.avatar_url}
            alt={user.login}
            className="w-24 h-24 rounded-2xl border-2 border-blue-500/50 shadow-lg"
          />
          <div className="absolute inset-0 rounded-2xl border-2 border-blue-500/30 animate-pulse" />
        </motion.div>

        {/* Info */}
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-3xl font-bold">{user.login}</h2>
            <Github className="w-6 h-6 text-blue-500" />
          </div>

          <p className="text-slate-400 mb-4">
            GitHub Developer • Active Contributor
          </p>

          <div className="flex flex-wrap gap-4 text-sm">
            {user.email && (
              <div className="flex items-center gap-2 text-slate-300">
                <Mail className="w-4 h-4 text-blue-500" />
                {user.email}
              </div>
            )}
            <div className="flex items-center gap-2 text-slate-300">
              <Github className="w-4 h-4 text-blue-500" />
              @{user.login}
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-4 md:gap-6">
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="text-center"
          >
            <div className="text-2xl font-bold text-blue-400">{totalCommits}</div>
            <div className="text-xs text-slate-400">Commits</div>
          </motion.div>
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="text-center"
          >
            <div className="text-2xl font-bold text-green-400">{totalRepos}</div>
            <div className="text-xs text-slate-400">Repos</div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}
