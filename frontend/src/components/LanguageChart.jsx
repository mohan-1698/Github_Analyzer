import { motion } from 'framer-motion'
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts'
import { Code } from 'lucide-react'
import { useState } from 'react'

const LanguageChart = ({ data }) => {
  const [hoveredLanguage, setHoveredLanguage] = useState(null)

  // Generate chart data from repositories
  const generateLanguageData = () => {
    const repos = data?.repos || []
    const languageMap = {}

    // Count repos by language - only include repos with actual language data
    repos.forEach(repo => {
      if (repo.language) { // Only add repos that have a language
        languageMap[repo.language] = (languageMap[repo.language] || 0) + 1
      }
    })

    // Convert to percentages and sort
    const reposWithLanguage = Object.values(languageMap).reduce((a, b) => a + b, 0) || 1
    const entries = Object.entries(languageMap)
      .map(([name, count]) => ({
        name,
        value: Math.round((count / reposWithLanguage) * 100),
        count,
        percentage: ((count / reposWithLanguage) * 100).toFixed(1)
      }))
      .sort((a, b) => b.count - a.count)

    return entries.length > 0 ? entries : []
  }

  const chartData = generateLanguageData()
  
  // Extended color palette for more languages
  const COLORS = [
    '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
    '#ef4444', '#06b6d4', '#ec4899', '#14b8a6',
    '#f97316', '#6366f1', '#84cc16', '#d946ef'
  ]

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload
      return (
        <div className="bg-slate-900 border border-blue-500 rounded-lg p-3 shadow-lg">
          <p className="font-semibold text-blue-400">{data.name}</p>
          <p className="text-slate-300 text-sm">{data.percentage}% ({data.count} repos)</p>
        </div>
      )
    }
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-hover p-6 rounded-xl h-full flex flex-col"
    >
      <div className="flex items-center gap-3 mb-6">
        <Code className="w-5 h-5 text-green-500" />
        <h3 className="text-xl font-bold">Language Distribution</h3>
      </div>

      {chartData.length > 0 ? (
        <div className="flex flex-col flex-1">
          {/* Pie Chart - Fixed Height */}
          <div className="h-64 -mx-6 px-6">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={75}
                  innerRadius={40}
                  animationDuration={800}
                  label={({ percentage }) => `${percentage}%`}
                >
                  {chartData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={COLORS[index % COLORS.length]}
                      opacity={hoveredLanguage === null || hoveredLanguage === entry.name ? 1 : 0.4}
                      style={{ cursor: 'pointer', transition: 'opacity 0.2s ease' }}
                      onClick={() => setHoveredLanguage(entry.name)}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Language List */}
          <div className="mt-4 pt-4 border-t border-slate-700 flex-1 flex flex-col">
            <div className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wide">
              All Languages ({chartData.length})
            </div>
            <div className="space-y-1.5 overflow-y-auto pr-2">
              {chartData.map((item, index) => (
                <motion.div
                  key={item.name}
                  onMouseEnter={() => setHoveredLanguage(item.name)}
                  onMouseLeave={() => setHoveredLanguage(null)}
                  whileHover={{ x: 4 }}
                  className="flex items-center justify-between p-2 rounded hover:bg-slate-800/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <div
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ 
                        backgroundColor: COLORS[index % COLORS.length],
                        opacity: hoveredLanguage === null || hoveredLanguage === item.name ? 1 : 0.4
                      }}
                    />
                    <span className="text-sm text-slate-300 truncate">{item.name}</span>
                  </div>
                  <div className="flex items-center gap-1.5 ml-2 flex-shrink-0">
                    <span className="text-sm font-semibold text-blue-400">{item.percentage}%</span>
                    <span className="text-xs text-slate-500">({item.count})</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="h-64 flex items-center justify-center text-slate-400">
          No repositories with assigned language data
        </div>
      )}
    </motion.div>
  )
}

export default LanguageChart
