import { useState, useEffect } from 'react'
import { ChevronRight, AlertTriangle, Shield } from 'lucide-react'
import { getAdvisorQueue } from '../services/api'
import { LoadingSpinner } from './LoadingState'
import EmptyState from './EmptyState'

export default function ReviewQueue({ onSelectCase }) {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAdvisorQueue()
      .then((r) => setList(r.queue || []))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 'var(--space-8)', justifyContent: 'center' }}>
        <LoadingSpinner />
        <span className="text-muted">Loading queue...</span>
      </div>
    )
  }

  if (list.length === 0) {
    return (
      <EmptyState
        icon={Shield}
        title="No pending cases"
        description="All cases have been reviewed. New cases will appear here when analyses are submitted."
      />
    )
  }

  return (
    <div className="queue-list">
      {list.map((c) => (
        <div
          key={c.case_id}
          className="queue-item"
          onClick={() => onSelectCase?.(c.case_id)}
        >
          <div className="queue-item-main">
            <div className="queue-item-info">
              <div className="queue-item-id">Case #{c.case_id}</div>
              <div className="queue-item-meta">
                <span>Income: ${c.income != null ? Number(c.income).toLocaleString() : '—'}</span>
                <span>{c.province ?? '—'}</span>
                <span>{Math.round((c.confidence_score ?? 0) * 100)}% confidence</span>
              </div>
              {c.flags?.length > 0 && (
                <div className="queue-item-flags" style={{ marginTop: 'var(--space-2)' }}>
                  {c.flags.map((flag, i) => (
                    <span key={i} className="badge badge-medium">
                      <AlertTriangle size={10} />
                      {flag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
          <ChevronRight size={20} className="queue-chevron" />
        </div>
      ))}
    </div>
  )
}
