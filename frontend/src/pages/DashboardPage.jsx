import { motion } from 'framer-motion'
import { RefreshCw, AlertCircle, GitBranch, GitCommit, Code } from 'lucide-react'
import Navbar from '../components/Navbar'
import ProfileCard from '../components/ProfileCard'
import ScoreCard from '../components/ScoreCard'
import CommitChart from '../components/CommitChart'
import LanguageChart from '../components/LanguageChart'
import InsightsPanel from '../components/InsightsPanel'
import { DashboardSkeleton } from '../components/LoadingAnimation'
import { useDashboard } from '../hooks/useDashboard'

export default function DashboardPage() {
  const { data, loading, error, syncing, syncGitHubData, calculateAnalytics, generateInsights } = useDashboard()

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="container-custom py-12">
          <DashboardSkeleton />
        </div>
      </>
    )
  }

  // Extract real data from GitHub
  const githubData = data?.github_data || {}
  const repos = githubData.repos || []
  const commits = githubData.commits || []
  const prs = githubData.prs || []
  const languages = githubData.profile?.language || {}

  return (
    <>
      <Navbar />

      <div className="min-h-screen bg-gradient-animated">
        <div className="container-custom py-12">
          {/* Error Alert */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-8 p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-start gap-3"
            >
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-400">Error</p>
                <p className="text-sm text-red-300">{error}</p>
              </div>
            </motion.div>
          )}

          {/* Header with Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between mb-12"
          >
            <h1 className="text-4xl font-bold">Dashboard</h1>
            <div className="flex gap-3">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={syncGitHubData}
                disabled={syncing}
                className="btn-primary flex items-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Syncing...' : 'Sync Data'}
              </motion.button>
            </div>
          </motion.div>

          {/* Profile Section */}
          {data?.user && (
            <div className="mb-12">
              <ProfileCard 
                user={data.user}
                stats={{
                  totalCommits: commits.length,
                  totalRepos: repos.length
                }}
              />
            </div>
          )}

          {/* Real GitHub Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 stagger-container">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-6 rounded-lg"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm mb-2">Total Repositories</p>
                  <p className="text-4xl font-bold text-blue-400">{repos.length}</p>
                </div>
                <GitBranch className="w-12 h-12 text-blue-500/50" />
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-card p-6 rounded-lg"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm mb-2">Total Commits (90d)</p>
                  <p className="text-4xl font-bold text-green-400">{commits.length}</p>
                </div>
                <GitCommit className="w-12 h-12 text-green-500/50" />
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-card p-6 rounded-lg"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm mb-2">Pull Requests (90d)</p>
                  <p className="text-4xl font-bold text-purple-400">{prs.length}</p>
                </div>
                <Code className="w-12 h-12 text-purple-500/50" />
              </div>
            </motion.div>
          </div>

          {/* Repositories List */}
          {repos.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-12"
            >
              <h2 className="text-2xl font-bold mb-6">Your Repositories ({repos.length})</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {repos.slice(0, 8).map((repo, idx) => (
                  <motion.a
                    key={repo.id}
                    href={repo.html_url || `https://github.com/${repo.owner?.login || data?.user?.login}/${repo.name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    whileHover={{ scale: 1.02, x: 5 }}
                    className="glass-card p-4 rounded-lg hover:border-blue-500/50 hover:bg-slate-800/60 transition-all cursor-pointer group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-blue-300 group-hover:text-blue-400 transition-colors flex items-center gap-2">
                          <Code className="w-4 h-4" />
                          {repo.name}
                        </h3>
                        <p className="text-xs text-slate-500">{repo.language || 'No language'}</p>
                      </div>
                      {repo.stargazers_count > 0 && (
                        <span className="bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded text-xs flex-shrink-0 ml-2">
                          ⭐ {repo.stargazers_count}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-400 line-clamp-2">{repo.description || 'No description'}</p>
                    <div className="flex gap-3 mt-4 text-xs text-slate-500">
                      <span>🔀 {repo.forks_count} forks</span>
                      <span>👁 {repo.watchers_count} watchers</span>
                    </div>
                    <div className="flex items-center gap-2 mt-3 text-blue-400 text-xs opacity-0 group-hover:opacity-100 transition-opacity">
                      <span>Visit Repository</span>
                      <span>→</span>
                    </div>
                  </motion.a>
                ))}
              </div>
              {repos.length > 8 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="mt-6 text-center"
                >
                  <a
                    href={`https://github.com/${data?.user?.login}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    View all {repos.length} repositories on GitHub →
                  </a>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
            <CommitChart data={githubData} />
            <LanguageChart data={githubData} />
          </div>

          {/* Insights Panel */}
          <InsightsPanel insights={data?.insights || []} />

          {/* Footer Stats */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-12 flex justify-center text-slate-400 text-sm"
          >
            <p>
              Last synced: {githubData.synced_at ? new Date(githubData.synced_at).toLocaleString() : 'Never'}
            </p>
          </motion.div>
        </div>
      </div>
    </>
  )
}
