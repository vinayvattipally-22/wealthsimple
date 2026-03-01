import { useState, useEffect } from 'react'
import {
  Shield, ChevronDown, ChevronUp, ChevronRight,
  Check, X, Clock, MessageSquare, Send,
  TrendingUp, TrendingDown, Minus, ExternalLink,
} from 'lucide-react'
import { LoadingSpinner } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import {
  getStockAdvisorQueue,
  approveStockInsight,
  rejectStockInsight,
} from '../services/api'
import '../styles/dashboard.css'

const STATUS_COLORS = {
  PENDING: 'var(--ws-amber)',
  APPROVED: 'var(--ws-green)',
  REJECTED: 'var(--ws-red)',
}

const DIRECTION_COLORS = {
  bullish: 'var(--ws-green)',
  bearish: '#ef4444',
  neutral: 'var(--ws-amber)',
}

const TIMEFRAME_LABELS = {
  short: 'Short Term (1-2 weeks)',
  mid: 'Mid Term (1-3 months)',
  long: 'Long Term (6-12 months)',
}

function DirectionIcon({ direction }) {
  if (direction === 'bullish') return <TrendingUp size={16} />
  if (direction === 'bearish') return <TrendingDown size={16} />
  return <Minus size={16} />
}

/* ── Single Insight Review Card ── */
function StockInsightReviewCard({ insight, onUpdate }) {
  const [expanded, setExpanded] = useState(false)
  const [comment, setComment] = useState(insight.advisor_comment || '')
  const [saving, setSaving] = useState(false)
  const [actionDone, setActionDone] = useState(null)

  const status = insight.review_status || 'PENDING'
  const isPending = status === 'PENDING'
  const displayStatus = actionDone || status

  const handleApprove = async () => {
    setSaving(true)
    try {
      await approveStockInsight(insight.id, comment)
      setActionDone('APPROVED')
      onUpdate?.(insight.id, 'APPROVED')
    } catch { /* silent */ }
    setSaving(false)
  }

  const handleReject = async () => {
    setSaving(true)
    try {
      await rejectStockInsight(insight.id, comment)
      setActionDone('REJECTED')
      onUpdate?.(insight.id, 'REJECTED')
    } catch { /* silent */ }
    setSaving(false)
  }

  return (
    <div className="advisor-insight-card" style={{ borderLeftColor: DIRECTION_COLORS[insight.direction] || '#666' }}>
      <div className="advisor-insight-header" onClick={() => setExpanded(!expanded)}>
        <div className="advisor-insight-title">
          <span className="stock-insight-direction-badge" style={{ color: DIRECTION_COLORS[insight.direction] }}>
            <DirectionIcon direction={insight.direction} />
            {insight.direction}
          </span>
          <span className="advisor-insight-headline">
            {TIMEFRAME_LABELS[insight.timeframe] || insight.timeframe}
          </span>
        </div>
        <div className="advisor-insight-right">
          {insight.confidence != null && (
            <span className="advisor-insight-value">
              {(insight.confidence * 100).toFixed(0)}% conf.
            </span>
          )}
          <span
            className="advisor-insight-status"
            style={{ color: STATUS_COLORS[displayStatus] || 'var(--ws-grey-500)' }}
          >
            {displayStatus}
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {expanded && (
        <div className="advisor-insight-body">
          {insight.reasoning && (
            <div className="advisor-insight-detail">
              <p>{insight.reasoning}</p>
            </div>
          )}

          {insight.referenced_articles?.length > 0 && (
            <div className="stock-review-sources">
              <strong>Referenced News:</strong>
              {insight.referenced_articles.map((a) => (
                <a
                  key={a.id}
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="stock-review-source-link"
                >
                  {a.title?.length > 70 ? a.title.slice(0, 70) + '...' : a.title}
                  <ExternalLink size={10} />
                </a>
              ))}
            </div>
          )}

          <div className="advisor-insight-meta">
            <span>Created: {insight.created_at ? new Date(insight.created_at).toLocaleString() : '—'}</span>
          </div>

          {/* Comment area */}
          <div className="advisor-comment-area">
            <label className="advisor-comment-label">
              <MessageSquare size={14} />
              Advisor Feedback
            </label>
            <textarea
              className="advisor-comment-input"
              placeholder="Add your comments on this insight..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              disabled={!isPending && !actionDone}
            />
          </div>

          {/* Action buttons */}
          {isPending && !actionDone && (
            <div className="advisor-insight-actions">
              <button className="btn btn-success btn-sm" onClick={handleApprove} disabled={saving}>
                {saving ? <LoadingSpinner size={12} /> : <Check size={14} />}
                Approve
              </button>
              <button className="btn btn-danger btn-sm" onClick={handleReject} disabled={saving}>
                {saving ? <LoadingSpinner size={12} /> : <X size={14} />}
                Reject
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Ticker Detail View ── */
function TickerDetailView({ group, onBack }) {
  const [insights, setInsights] = useState(group.insights || [])

  const handleUpdate = (insightId, newStatus) => {
    setInsights(prev =>
      prev.map(i => i.id === insightId ? { ...i, review_status: newStatus } : i)
    )
  }

  const pendingCount = insights.filter(i => i.review_status === 'PENDING').length
  const approvedCount = insights.filter(i => i.review_status === 'APPROVED').length
  const rejectedCount = insights.filter(i => i.review_status === 'REJECTED').length

  return (
    <div className="animate-fade-in">
      <div className="advisor-case-header">
        <div className="advisor-case-header-left">
          <button className="btn btn-ghost btn-sm" onClick={onBack}>
            <ChevronDown size={16} style={{ transform: 'rotate(90deg)' }} /> Back
          </button>
          <h2 className="heading-2" style={{ margin: 0 }}>
            {group.ticker}
          </h2>
          {group.company_name && (
            <span className="text-muted">{group.company_name}</span>
          )}
        </div>
      </div>

      {/* Review progress */}
      <div className="advisor-review-progress">
        <span className="advisor-progress-item" style={{ color: 'var(--ws-green)' }}>
          <Check size={14} /> {approvedCount} approved
        </span>
        <span className="advisor-progress-item" style={{ color: 'var(--ws-red)' }}>
          <X size={14} /> {rejectedCount} rejected
        </span>
        <span className="advisor-progress-item" style={{ color: 'var(--ws-amber)' }}>
          <Clock size={14} /> {pendingCount} pending
        </span>
      </div>

      <h3 className="heading-3" style={{ marginTop: 'var(--space-6)' }}>
        Stock Insights ({insights.length})
      </h3>

      {insights.length === 0 ? (
        <EmptyState title="No insights" description="No stock insights to review for this ticker." />
      ) : (
        <div className="advisor-insights-list">
          {insights.map((ins) => (
            <StockInsightReviewCard
              key={ins.id}
              insight={ins}
              onUpdate={handleUpdate}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/* ── Queue View ── */
function StockQueueView({ onSelectTicker }) {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('PENDING')

  useEffect(() => {
    setLoading(true)
    getStockAdvisorQueue(filter)
      .then((r) => setGroups(r.queue || []))
      .finally(() => setLoading(false))
  }, [filter])

  return (
    <>
      <div className="advisor-filter-tabs">
        {['PENDING', 'APPROVED', 'REJECTED', 'ALL'].map((s) => (
          <button
            key={s}
            className={`advisor-filter-tab ${filter === s ? 'advisor-filter-active' : ''}`}
            onClick={() => setFilter(s)}
          >
            {s === 'ALL' ? 'All' : s.charAt(0) + s.slice(1).toLowerCase()}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 'var(--space-8)', justifyContent: 'center' }}>
          <LoadingSpinner />
          <span className="text-muted">Loading queue...</span>
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          icon={Shield}
          title={filter === 'PENDING' ? 'No pending stock insights' : `No ${filter.toLowerCase()} stock insights`}
          description={filter === 'PENDING'
            ? 'All stock insights have been reviewed.'
            : 'No stock insights match this filter.'}
        />
      ) : (
        <div className="advisor-queue-list">
          {groups.map((g) => (
            <div
              key={g.ticker}
              className="advisor-queue-card"
              onClick={() => onSelectTicker?.(g)}
            >
              <div className="advisor-queue-card-top">
                <div className="advisor-queue-card-id">
                  <TrendingUp size={16} />
                  {g.ticker}
                </div>
                {g.pending_count > 0 && (
                  <span
                    className="advisor-status-badge"
                    style={{ backgroundColor: STATUS_COLORS.PENDING }}
                  >
                    {g.pending_count} pending
                  </span>
                )}
              </div>
              <div className="advisor-queue-card-info">
                {g.company_name && <span>{g.company_name}</span>}
                <span>{g.total_count} insight{g.total_count !== 1 ? 's' : ''}</span>
              </div>
              <ChevronRight size={18} className="advisor-queue-chevron" />
            </div>
          ))}
        </div>
      )}
    </>
  )
}

/* ── Main Page ── */
export default function StockAdvisorReview() {
  const [selectedGroup, setSelectedGroup] = useState(null)

  return (
    <div className="page-container animate-fade-in">
      {!selectedGroup && (
        <div className="page-header">
          <div className="page-header-text">
            <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Shield size={24} />
              Stock Insights Review
            </h1>
            <p className="page-subtitle">
              Verify AI-generated stock insights before they reach users.
            </p>
          </div>
        </div>
      )}
      {selectedGroup ? (
        <TickerDetailView group={selectedGroup} onBack={() => setSelectedGroup(null)} />
      ) : (
        <StockQueueView onSelectTicker={setSelectedGroup} />
      )}
    </div>
  )
}
