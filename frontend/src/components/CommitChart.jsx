import { useState } from 'react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Calendar, TrendingUp } from 'lucide-react'

const CommitChart = ({ data }) => {
  const [timePeriod, setTimePeriod] = useState('daily') // daily, weekly, monthly, yearly

  const getCommitDate = (commit) => {
    // Handle different date field locations
    const dateStr = 
      commit.committed_at || 
      commit.date ||
      commit.commit?.committer?.date ||
      commit.commit?.author?.date
    
    if (!dateStr) return null
    
    try {
      return new Date(dateStr)
    } catch (e) {
      console.warn('Failed to parse commit date:', dateStr)
      return null
    }
  }

  const generateChartData = () => {
    const commits = data?.commits || []
    
    // Filter out commits with invalid dates
    const validCommits = commits.filter(commit => {
      const date = getCommitDate(commit)
      return date !== null && !isNaN(date.getTime())
    })
    
    if (validCommits.length === 0) {
      console.warn('No valid commits with proper dates found. Total commits:', commits.length)
      console.warn('Sample commit:', commits[0])
      return []
    }
    
    if (timePeriod === 'daily') {
      // Show last 7 days with actual dates
      const dateMap = {}
      const today = new Date()
      
      // Initialize last 7 days (going backwards)
      for (let i = 6; i >= 0; i--) {
        const date = new Date(today)
        date.setDate(date.getDate() - i)
        const dateStr = date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric',
          weekday: 'short'
        })
        dateMap[dateStr] = 0
      }
      
      // Count commits for each day
      validCommits.forEach(commit => {
        const commitDate = getCommitDate(commit)
        if (commitDate) {
          const dateStr = commitDate.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            weekday: 'short'
          })
          if (dateMap.hasOwnProperty(dateStr)) {
            dateMap[dateStr]++
          }
        }
      })
      
      return Object.entries(dateMap).map(([date, count]) => ({ date, commits: count }))
    } 
    else if (timePeriod === 'weekly') {
      // Show last 4 weeks grouped by week with date ranges
      const weekMap = {}
      const weekDates = {} // Store date ranges
      const today = new Date()
      
      // Initialize last 4 weeks with date ranges
      for (let i = 3; i >= 0; i--) {
        const weekStart = new Date(today)
        weekStart.setDate(weekStart.getDate() - (i * 7))
        
        const weekEnd = new Date(weekStart)
        weekEnd.setDate(weekEnd.getDate() + 6)
        
        const startStr = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        const endStr = weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        const weekStr = `${startStr} - ${endStr}`
        
        if (!weekMap.hasOwnProperty(weekStr)) {
          weekMap[weekStr] = 0
          weekDates[weekStr] = { start: weekStart, end: weekEnd }
        }
      }
      
      // Count commits by week based on date ranges
      validCommits.forEach(commit => {
        const commitDate = getCommitDate(commit)
        if (commitDate) {
          // Find which week this commit belongs to
          for (const [weekStr, dateRange] of Object.entries(weekDates)) {
            if (commitDate >= dateRange.start && commitDate <= dateRange.end) {
              weekMap[weekStr]++
              break
            }
          }
        }
      })
      
      return Object.entries(weekMap).map(([date, count]) => ({ date, commits: count }))
    }
    else if (timePeriod === 'monthly') {
      // Show last 12 months with actual day-wise breakdown by month
      const monthMap = {}
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      
      // Initialize all 12 months
      monthNames.forEach(month => { monthMap[month] = 0 })
      
      // Count commits by month
      validCommits.forEach(commit => {
        const commitDate = getCommitDate(commit)
        if (commitDate) {
          const monthStr = monthNames[commitDate.getMonth()]
          monthMap[monthStr]++
        }
      })
      
      return monthNames.map(month => ({ date: month, commits: monthMap[month] }))
    }
    else { // yearly
      // Show commits by year
      const yearMap = {}
      
      validCommits.forEach(commit => {
        const commitDate = getCommitDate(commit)
        if (commitDate) {
          const year = commitDate.getFullYear()
          const yearStr = `${year}`
          yearMap[yearStr] = (yearMap[yearStr] || 0) + 1
        }
      })
      
      // Sort by year
      const sortedYears = Object.keys(yearMap).sort((a, b) => parseInt(a) - parseInt(b))
      return sortedYears.map(year => ({ date: year, commits: yearMap[year] }))
    }
  }

  // Calculate statistics
  const chartData = generateChartData()
  const totalCommits = chartData.reduce((sum, item) => sum + item.commits, 0)
  const activeDays = chartData.filter(item => item.commits > 0).length
  const avgDaily = activeDays > 0 ? (totalCommits / activeDays).toFixed(1) : 0
  
  // Find highest commits
  let highestCommit = 0
  let highestCommitDate = 'N/A'
  chartData.forEach(item => {
    if (item.commits > highestCommit) {
      highestCommit = item.commits
      highestCommitDate = item.date
    }
  })

  const periodLabels = {
    daily: 'Last 7 Days (Daily)',
    weekly: 'Last 4 Weeks (Weekly)',
    monthly: 'Last 12 Months (Monthly)',
    yearly: 'By Year'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="glass-hover p-6 rounded-xl"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Calendar className="w-5 h-5 text-blue-500" />
          <h3 className="text-xl font-bold">Commits - {periodLabels[timePeriod]}</h3>
        </div>
        <select
          value={timePeriod}
          onChange={(e) => setTimePeriod(e.target.value)}
          className="px-3 py-1 bg-slate-700/50 border border-blue-500/30 rounded text-sm text-slate-200 cursor-pointer hover:border-blue-500/60 transition-colors"
        >
          <option value="daily">Last 7 Days</option>
          <option value="weekly">Last 4 Weeks</option>
          <option value="monthly">Last 12 Months</option>
          <option value="yearly">By Year</option>
        </select>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="colorCommits" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis 
            dataKey="date" 
            stroke="#64748b"
            angle={timePeriod === 'daily' ? -45 : 0}
            textAnchor={timePeriod === 'daily' ? 'end' : 'middle'}
            height={timePeriod === 'daily' ? 80 : 40}
          />
          <YAxis stroke="#64748b" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #3b82f6',
              borderRadius: '8px',
              boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)',
            }}
            labelStyle={{ color: '#e2e8f0' }}
            formatter={(value) => [value + ' commits', 'Commits']}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="commits"
            stroke="#3b82f6"
            strokeWidth={3}
            dot={{ fill: '#3b82f6', r: 5 }}
            activeDot={{ r: 7, fill: '#60a5fa' }}
            animationDuration={800}
            fillOpacity={1}
            fill="url(#colorCommits)"
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        <motion.div whileHover={{ scale: 1.05 }} className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
          <div className="text-2xl font-bold text-blue-400">{totalCommits}</div>
          <div className="text-xs text-slate-400">Total Commits</div>
        </motion.div>
        <motion.div whileHover={{ scale: 1.05 }} className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
          <div className="text-2xl font-bold text-green-400">{avgDaily}</div>
          <div className="text-xs text-slate-400">Daily Avg</div>
        </motion.div>
        <motion.div whileHover={{ scale: 1.05 }} className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
          <div className="text-2xl font-bold text-purple-400">{activeDays}</div>
          <div className="text-xs text-slate-400">Active Days</div>
        </motion.div>
        <motion.div whileHover={{ scale: 1.05 }} className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/30">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-orange-400" />
            <div>
              <div className="text-lg font-bold text-orange-400">{highestCommit}</div>
              <div className="text-xs text-slate-400">Peak: {highestCommitDate}</div>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}

export default CommitChart
