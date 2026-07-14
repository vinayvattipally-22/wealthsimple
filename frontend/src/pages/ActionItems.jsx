import { useState, useEffect } from 'react'
import { ListChecks, ChevronDown, CheckCircle2, Clock, AlertTriangle, SkipForward, ChevronRight, Zap } from 'lucide-react'
import { PageLoading } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import ReviewPendingBanner from '../components/ReviewPendingBanner'
import FormattedText from '../components/FormattedText'
import { getActionItems, updateActionItem, getUserDocuments } from '../services/api'
import { usePageData } from '../context/PageDataContext'
import '../styles/dashboard.css'

function isOverdue(deadline) {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}

function isThisWeek(deadline) {
  if (!deadline) return false
  const d = new Date(deadline)
  const now = new Date()
  const diff = (d - now) / (1000 * 60 * 60 * 24)
  return diff >= 0 && diff <= 7
}

function isThisMonth(deadline) {
  if (!deadline) return false
  const d = new Date(deadline)
  const now = new Date()
  const diff = (d - now) / (1000 * 60 * 60 * 24)
  return diff > 7 && diff <= 30
}

function formatDeadline(deadline) {
  if (!deadline) return 'Ongoing'
  const d = new Date(deadline)
  return d.toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })
}

function ActionItemCard({ item, onUpdate }) {
  const [expanded, setExpanded] = useState(false)
  const overdue = isOverdue(item.deadline)
  const done = item.status === 'completed' || item.status === 'skipped'

  const handleToggleComplete = async (e) => {
    e.stopPropagation()
    const newStatus = item.status === 'completed' ? 'pending' : 'completed'
    await onUpdate(item.id, newStatus)
  }

  const handleSkip = async (e) => {
    e.stopPropagation()
    await onUpdate(item.id, 'skipped')
  }

  return (
    <div
      className={`action-item-card ${done ? 'action-item-done' : ''} ${overdue && !done ? 'action-item-overdue' : ''}`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="action-item-row">
        <button
          className={`action-item-check ${done ? 'action-item-checked' : ''}`}
          onClick={handleToggleComplete}
          title={done ? 'Mark pending' : 'Mark complete'}
        >
          {done ? <CheckCircle2 size={18} /> : <div className="action-item-circle" />}
        </button>
        <div className="action-item-content">
          <div className={`action-item-title ${done ? 'action-item-title-done' : ''}`}>
            {item.title}
          </div>
          <div className="action-item-meta">
            {item.ai_score != null && (
              <span
                className="ai-score-badge"
                style={{
                  background: item.ai_score >= 70 ? 'var(--ws-red)' : item.ai_score >= 40 ? 'var(--ws-amber)' : 'var(--ws-grey-400)',
                  color: '#fff',
                  padding: '1px 7px',
                  borderRadius: '10px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px',
                }}
                title="AI Priority Score"
              >
                <Zap size={10} /> {item.ai_score}
              </span>
            )}
            {item.deadline && (
              <span className={`action-item-deadline ${overdue && !done ? 'text-red' : ''}`}>
                <Clock size={12} />
                {formatDeadline(item.deadline)}
              </span>
            )}
            {!item.deadline && (
              <span className="action-item-deadline text-muted">
                <Clock size={12} /> Ongoing
              </span>
            )}
            <span className={`badge badge-${(item.priority || 'medium').toLowerCase()}`}>
              {item.priority}
            </span>
            {item.estimated_value > 0 && (
              <span className="text-green font-semibold">
                ${Number(item.estimated_value).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
              </span>
            )}
          </div>
          {item.ai_reasoning && !done && (
            <div style={{ fontSize: '0.75rem', color: 'var(--ws-grey-500)', marginTop: 2 }}>
              <Zap size={10} style={{ verticalAlign: 'middle', marginRight: 3 }} />
              {item.ai_reasoning}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {!done && item.status !== 'skipped' && (
            <button className="btn btn-ghost btn-sm" onClick={handleSkip} title="Skip">
              <SkipForward size={14} />
            </button>
          )}
          <ChevronRight
            size={16}
            className="action-item-chevron"
            style={{ transform: expanded ? 'rotate(90deg)' : 'none', transition: 'var(--transition-fast)' }}
          />
        </div>
      </div>
      {expanded && item.description && (
        <div className="action-item-detail">
          <FormattedText text={item.description} />
        </div>
      )}
    </div>
  )
}

function ItemGroup({ title, icon: Icon, items, color, onUpdate }) {
  if (items.length === 0) return null
  return (
    <div className="action-group">
      <div className="action-group-header" style={{ color }}>
        <Icon size={16} />
        <span>{title}</span>
        <span className="action-group-count">{items.length}</span>
      </div>
      {items.map((item) => (
        <ActionItemCard key={item.id} item={item} onUpdate={onUpdate} />
      ))}
    </div>
  )
}

export default function ActionItems() {
  const [profiles, setProfiles] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const { setPageData } = usePageData()

  // Load profiles
  useEffect(() => {
    getUserDocuments()
      .then((res) => {
        const docs = (res.documents || []).filter(d => d.profile_id)
        setProfiles(docs)
        if (docs.length > 0) setSelectedId(docs[0].profile_id)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Fetch action items
  useEffect(() => {
    if (!selectedId) return
    setLoading(true)
    getActionItems(selectedId)
      .then((res) => {
        setData(res)
        setPageData({ page: 'action_items', data: res })
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [selectedId, setPageData])

  const handleUpdate = async (itemId, newStatus) => {
    try {
      await updateActionItem(itemId, { status: newStatus })
      // Refresh
      const refreshed = await getActionItems(selectedId)
      setData(refreshed)
    } catch {
      // silent
    }
  }

  if (loading) return <PageLoading />

  if (profiles.length === 0) {
    return (
      <div className="page-container">
        <EmptyState
          icon={ListChecks}
          title="No action items yet"
          description="Upload a document and run an analysis to generate action items."
        />
      </div>
    )
  }

  const items = data?.action_items || []
  const summary = data?.summary || {}
  const activeItems = items.filter(i => i.status !== 'completed' && i.status !== 'skipped')
  const completedItems = items.filter(i => i.status === 'completed' || i.status === 'skipped')

  const overdue = activeItems.filter(i => isOverdue(i.deadline))
  const thisWeek = activeItems.filter(i => !isOverdue(i.deadline) && isThisWeek(i.deadline))
  const thisMonth = activeItems.filter(i => !isOverdue(i.deadline) && !isThisWeek(i.deadline) && isThisMonth(i.deadline))
  const later = activeItems.filter(i => !isOverdue(i.deadline) && !isThisWeek(i.deadline) && !isThisMonth(i.deadline))

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">Action Items</h1>
          <p className="page-subtitle">
            {summary.pending > 0 ? `${summary.pending} pending` : 'All caught up'}
            {summary.total_savings > 0 && ` · $${Number(summary.total_savings).toLocaleString('en-CA', { minimumFractionDigits: 2 })} in potential savings`}
          </p>
        </div>
        {profiles.length > 0 && (
          <div className="dashboard-select-wrap">
            <select
              className="dashboard-select"
              value={selectedId || ''}
              onChange={(e) => setSelectedId(Number(e.target.value))}
            >
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.tax_year || 'N/A'}{p.doc_type ? ` — ${p.doc_type}` : ''}
                </option>
              ))}
            </select>
            <ChevronDown size={16} className="dashboard-select-icon" />
          </div>
        )}
      </div>

      {/* Summary cards */}
      <div className="summary-grid" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="summary-card">
          <div className="summary-card-label">Pending</div>
          <div className="summary-card-value">{summary.pending || 0}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-label">Completed</div>
          <div className="summary-card-value text-green">{summary.completed || 0}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-label">Potential Savings</div>
          <div className="summary-card-value text-green">
            ${Number(summary.total_savings || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      {items.length === 0 && data?.review_pending ? (
        <ReviewPendingBanner message="Your action items are linked to AI-generated insights that are currently under advisor review. They will appear here once approved." />
      ) : items.length === 0 ? (
        <EmptyState
          icon={ListChecks}
          title="No action items yet"
          description="Run an analysis to generate action items with deadlines."
        />
      ) : (
        <div>
          <ItemGroup title="Overdue" icon={AlertTriangle} items={overdue} color="var(--ws-red)" onUpdate={handleUpdate} />
          <ItemGroup title="This Week" icon={Clock} items={thisWeek} color="var(--ws-amber)" onUpdate={handleUpdate} />
          <ItemGroup title="This Month" icon={Clock} items={thisMonth} color="var(--ws-blue)" onUpdate={handleUpdate} />
          <ItemGroup title="Later / Ongoing" icon={ListChecks} items={later} color="var(--ws-grey-500)" onUpdate={handleUpdate} />
          {completedItems.length > 0 && (
            <ItemGroup title="Completed" icon={CheckCircle2} items={completedItems} color="var(--ws-green)" onUpdate={handleUpdate} />
          )}
        </div>
      )}
    </div>
  )
}
