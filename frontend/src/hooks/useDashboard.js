import { useState, useEffect, useCallback } from 'react'
import { dashboardAPI, githubAPI, analyticsAPI, insightsAPI } from '../utils/api'

export const useDashboard = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [syncing, setSyncing] = useState(false)

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await dashboardAPI.getDashboardData()
      console.log('Dashboard Data:', response.data)
      console.log('   User:', response.data?.user)
      console.log('   GitHub Data:', response.data?.github_data)
      console.log('   Repos Count:', response.data?.github_data?.repos?.length || 0)
      console.log('   Commits Count:', response.data?.github_data?.commits?.length || 0)
      console.log('   PRs Count:', response.data?.github_data?.prs?.length || 0)
      setData(response.data)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load dashboard')
      console.error('Dashboard error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const calculateAnalytics = useCallback(async () => {
    try {
      console.log('Calculating analytics...')
      await analyticsAPI.calculate()
      console.log('Analytics calculated')
    } catch (err) {
      console.error('Analytics error:', err.response?.data?.message || err.message)
    }
  }, [])

  const generateInsights = useCallback(async () => {
    try {
      console.log('Generating AI Insights...')
      const insightsResponse = await insightsAPI.generate()
      console.log('Insights Generated:', insightsResponse.data)
    } catch (err) {
      console.warn('Insights error (non-blocking):', err.response?.data?.message || err.message)
    }
  }, [])

  const syncGitHubData = useCallback(async () => {
    try {
      setSyncing(true)
      console.log('Starting GitHub sync...')
      const syncResponse = await githubAPI.syncData()
      console.log('Sync Response:', syncResponse.data)
      console.log('   Status:', syncResponse.data?.status)
      console.log('   Repos fetched:', syncResponse.data?.repos_count)
      console.log('   Commits fetched:', syncResponse.data?.commits_count)
      console.log('   PRs fetched:', syncResponse.data?.prs_count)
      
      // Step 1: Calculate analytics
      console.log('Step 1: Calculating analytics...')
      await calculateAnalytics()
      
      // Step 2: Generate insights
      console.log('Step 2: Generating insights...')
      await generateInsights()
      
      // Step 3: Fetch updated dashboard
      console.log('Step 3: Fetching updated dashboard data...')
      await fetchDashboardData()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to sync GitHub data')
      console.error('Sync error:', err.response?.data || err.message)
    } finally {
      setSyncing(false)
    }
  }, [fetchDashboardData, calculateAnalytics, generateInsights])

  useEffect(() => {
    const initData = async () => {
      console.log('Initializing dashboard...')
      await fetchDashboardData()
      
      // Auto-sync after initial load
      setTimeout(async () => {
        try {
          console.log('Auto-syncing GitHub data...')
          await syncGitHubData()
        } catch (err) {
          console.warn('Auto-sync failed:', err.message)
        }
      }, 1500)
    }
    
    initData()
  }, [])

  return {
    data,
    loading,
    error,
    syncing,
    fetchDashboardData,
    syncGitHubData,
    calculateAnalytics,
    generateInsights,
  }
}
