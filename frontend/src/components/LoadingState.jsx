import { Loader2 } from 'lucide-react'

export function LoadingSpinner({ size = 24 }) {
  return <Loader2 size={size} className="animate-spin" style={{ color: 'var(--ws-grey-400)' }} />
}

export function PageLoading() {
  return (
    <div className="page-container">
      <div className="skeleton skeleton-heading" style={{ width: '200px' }} />
      <div className="summary-cards">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="skeleton skeleton-card" />
        ))}
      </div>
      <div className="charts-grid">
        <div className="skeleton skeleton-chart" />
        <div className="skeleton skeleton-chart" />
      </div>
    </div>
  )
}
