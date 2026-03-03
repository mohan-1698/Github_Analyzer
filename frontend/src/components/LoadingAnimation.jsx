import { motion } from 'framer-motion'

export function SkeletonBar() {
  return (
    <motion.div
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ duration: 1.5, repeat: Infinity }}
      className="skeleton h-4 rounded-full"
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="glass p-6 rounded-xl">
      <div className="flex items-start gap-4 mb-4">
        <SkeletonBar className="w-12 h-12 rounded-lg" />
        <div className="flex-1 space-y-2">
          <SkeletonBar className="h-4 w-1/3" />
          <SkeletonBar className="h-3 w-1/2" />
        </div>
      </div>
      <SkeletonBar className="h-8 w-1/4 mb-4" />
      <SkeletonBar className="h-2 w-full mb-2" />
      <SkeletonBar className="h-2 w-2/3" />
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Profile Skeleton */}
      <SkeletonCard />

      {/* Metrics Grid Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      {/* Charts Grid Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[1, 2].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      {/* Insights Skeleton */}
      <SkeletonCard />
    </div>
  )
}

export function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        className="w-12 h-12 border-4 border-slate-700 border-t-blue-500 rounded-full"
      />
      <p className="text-slate-400">Loading your GitHub data...</p>
    </div>
  )
}

export default { SkeletonBar, SkeletonCard, DashboardSkeleton, LoadingSpinner }
