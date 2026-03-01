import { useState, useEffect } from 'react'
import {
  Shield, ChevronLeft, ChevronRight, ChevronDown, ChevronUp,
  Check, X, AlertTriangle, Clock, User, DollarSign, Percent,
  MessageSquare, Send, FileText, Eye,
} from 'lucide-react'
import { LoadingSpinner } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import FormattedText from '../components/FormattedText'
import PdfViewerModal from '../components/PdfViewerModal'
import {
  getAdvisorQueue, getCase, approveCase, rejectCase, escalateCase,
  approveInsight, rejectInsight, commentInsight,
} from '../services/api'
import '../styles/dashboard.css'

const STATUS_COLORS = {
  PENDING: 'var(--ws-amber)',
  APPROVED: 'var(--ws-green)',
  REJECTED: 'var(--ws-red)',
  ESCALATED: 'var(--ws-blue)',
}

const PRIORITY_CLASS = { HIGH: 'badge-red', MEDIUM: 'badge-amber', LOW: 'badge-grey' }
const CATEGORY_COLORS = { ACT_NOW: '#dc2626', THIS_YEAR: '#d97706', LONG_TERM: '#16a34a' }

function fmt(v) {
  return `$${Number(v || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}`
}

/* ── Insight Review Card ── */
function InsightReviewCard({ insight, caseId, onUpdate }) {
  const [expanded, setExpanded] = useState(false)
  const [comment, setComment] = useState(insight.advisor_comment || '')
  const [saving, setSaving] = useState(false)
  const [actionDone, setActionDone] = useState(null)

  const status = insight.review_status || 'PENDING'
  const isPending = status === 'PENDING'
  const catColor = CATEGORY_COLORS[insight.category] || '#666'

  const handleApprove = async () => {
    setSaving(true)
    try {
      await approveInsight(caseId, insight.id, comment)
      setActionDone('APPROVED')
      onUpdate?.(insight.id, 'APPROVED', comment)
    } catch { /* silent */ }
    setSaving(false)
  }

  const handleReject = async () => {
    setSaving(true)
    try {
      await rejectInsight(caseId, insight.id, comment)
      setActionDone('REJECTED')
      onUpdate?.(insight.id, 'REJECTED', comment)
    } catch { /* silent */ }
    setSaving(false)
  }

  const handleSaveComment = async () => {
    setSaving(true)
    try {
      await commentInsight(caseId, insight.id, comment)
    } catch { /* silent */ }
    setSaving(false)
  }

  const displayStatus = actionDone || status

  return (
    <div className="advisor-insight-card" style={{ borderLeftColor: catColor }}>
      {/* Header row */}
      <div className="advisor-insight-header" onClick={() => setExpanded(!expanded)}>
        <div className="advisor-insight-title">
          <span className={`badge ${PRIORITY_CLASS[insight.priority] || 'badge-grey'}`}>
            {insight.priority}
          </span>
          <span className="advisor-insight-headline">{insight.headline}</span>
        </div>
        <div className="advisor-insight-right">
          {insight.estimated_value > 0 && (
            <span className="advisor-insight-value">{fmt(insight.estimated_value)}</span>
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

      {/* Expanded detail */}
      {expanded && (
        <div className="advisor-insight-body">
          {insight.detail && (
            <div className="advisor-insight-detail">
              <FormattedText text={insight.detail} />
            </div>
          )}
          {insight.calculation_shown && (
            <div className="advisor-calc-block">
              <strong>Calculation:</strong>
              <pre>{insight.calculation_shown}</pre>
            </div>
          )}
          {insight.action_required && (
            <div className="advisor-action-required">
              <strong>Action Required:</strong> {insight.action_required}
            </div>
          )}
          <div className="advisor-insight-meta">
            <span>Confidence: {insight.confidence != null ? `${Math.round(insight.confidence * 100)}%` : '—'}</span>
            <span>Category: {insight.category}</span>
            <span>Type: {insight.insight_type}</span>
          </div>

          {/* Comment / feedback area */}
          <div className="advisor-comment-area">
            <label className="advisor-comment-label">
              <MessageSquare size={14} />
              Advisor Feedback
            </label>
            <textarea
              className="advisor-comment-input"
              placeholder="Add your comments or feedback on this insight..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              disabled={!isPending && !actionDone}
            />
            {insight.reviewed_at && !actionDone && (
              <div className="advisor-reviewed-info">
                Reviewed {new Date(insight.reviewed_at).toLocaleDateString('en-CA')}
              </div>
            )}
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
              {comment && (
                <button className="btn btn-secondary btn-sm" onClick={handleSaveComment} disabled={saving}>
                  <Send size={14} /> Save Comment
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Case Detail View ── */
function CaseDetailView({ caseId, onBack }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [bulkAction, setBulkAction] = useState(null)
  const [viewingDoc, setViewingDoc] = useState(null)

  useEffect(() => {
    if (!caseId) return
    setLoading(true)
    getCase(caseId).then(setData).finally(() => setLoading(false))
  }, [caseId])

  const handleInsightUpdate = (insightId, newStatus, comment) => {
    setData(prev => {
      if (!prev) return prev
      return {
        ...prev,
        insights: prev.insights.map(i =>
          i.id === insightId
            ? { ...i, review_status: newStatus, advisor_comment: comment }
            : i
        ),
      }
    })
  }

  const handleBulkApprove = async () => {
    setBulkAction('approving')
    try {
      await approveCase(caseId)
      setData(prev => prev ? {
        ...prev,
        status: 'APPROVED',
        insights: prev.insights.map(i => ({ ...i, review_status: 'APPROVED' })),
      } : prev)
    } catch { /* silent */ }
    setBulkAction(null)
  }

  const handleBulkReject = async () => {
    setBulkAction('rejecting')
    try {
      await rejectCase(caseId)
      setData(prev => prev ? {
        ...prev,
        status: 'REJECTED',
        insights: prev.insights.map(i => ({ ...i, review_status: 'REJECTED' })),
      } : prev)
    } catch { /* silent */ }
    setBulkAction(null)
  }

  const handleEscalate = async () => {
    setBulkAction('escalating')
    try {
      await escalateCase(caseId)
      setData(prev => prev ? { ...prev, status: 'ESCALATED' } : prev)
    } catch { /* silent */ }
    setBulkAction(null)
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 'var(--space-8)', justifyContent: 'center' }}>
        <LoadingSpinner />
        <span className="text-muted">Loading case...</span>
      </div>
    )
  }

  if (!data) return <EmptyState title="Case not found" description="This case could not be loaded." />

  const insights = data.insights || []
  const ps = data.profile_summary || {}
  const caseStatus = data.status
  const isPending = caseStatus === 'PENDING'
  const pendingCount = insights.filter(i => i.review_status === 'PENDING').length
  const approvedCount = insights.filter(i => i.review_status === 'APPROVED').length
  const rejectedCount = insights.filter(i => i.review_status === 'REJECTED').length

  return (
    <div className="animate-fade-in">
      {/* Back + Case header */}
      <div className="advisor-case-header">
        <div className="advisor-case-header-left">
          <button className="btn btn-ghost btn-sm" onClick={onBack}>
            <ChevronLeft size={16} /> Back
          </button>
          <h2 className="heading-2" style={{ margin: 0 }}>Case #{caseId}</h2>
          <span
            className="advisor-status-badge"
            style={{ backgroundColor: STATUS_COLORS[caseStatus] || 'var(--ws-grey-400)' }}
          >
            {caseStatus}
          </span>
        </div>
        {isPending && (
          <div className="advisor-case-actions">
            <button className="btn btn-success btn-sm" onClick={handleBulkApprove} disabled={!!bulkAction}>
              {bulkAction === 'approving' ? <LoadingSpinner size={12} /> : <Check size={14} />}
              Approve All
            </button>
            <button className="btn btn-danger btn-sm" onClick={handleBulkReject} disabled={!!bulkAction}>
              {bulkAction === 'rejecting' ? <LoadingSpinner size={12} /> : <X size={14} />}
              Reject All
            </button>
            <button className="btn btn-secondary btn-sm" onClick={handleEscalate} disabled={!!bulkAction}>
              <AlertTriangle size={14} /> Escalate
            </button>
          </div>
        )}
      </div>

      {/* Client + Profile summary */}
      <div className="advisor-profile-grid">
        <div className="advisor-profile-card">
          <div className="advisor-profile-card-label"><User size={14} /> Client</div>
          <div className="advisor-profile-card-value">{data.user_name || 'Unknown'}</div>
          <div className="advisor-profile-card-sub">{data.user_email || ''}</div>
        </div>
        <div className="advisor-profile-card">
          <div className="advisor-profile-card-label"><FileText size={14} /> Tax Year</div>
          <div className="advisor-profile-card-value">{data.tax_year} — {data.province}</div>
        </div>
        <div className="advisor-profile-card">
          <div className="advisor-profile-card-label"><DollarSign size={14} /> Income</div>
          <div className="advisor-profile-card-value">{fmt(ps.income)}</div>
        </div>
        <div className="advisor-profile-card">
          <div className="advisor-profile-card-label"><DollarSign size={14} /> Tax Liability</div>
          <div className="advisor-profile-card-value" style={{ color: 'var(--ws-red)' }}>{fmt(ps.tax_liability)}</div>
        </div>
        <div className="advisor-profile-card">
          <div className="advisor-profile-card-label"><Percent size={14} /> Marginal Rate</div>
          <div className="advisor-profile-card-value">
            {ps.marginal_rate != null ? `${(ps.marginal_rate * 100).toFixed(1)}%` : '—'}
          </div>
        </div>
        <div className="advisor-profile-card">
          <div className="advisor-profile-card-label">Confidence</div>
          <div className="advisor-profile-card-value">
            {data.confidence_score != null ? `${Math.round(data.confidence_score * 100)}%` : '—'}
          </div>
        </div>
      </div>

      {/* Source Documents */}
      {data.documents?.some(d => d.has_redacted_pdf) && (
        <div className="advisor-documents-bar">
          <FileText size={14} />
          <span className="advisor-documents-label">Source Documents:</span>
          {data.documents.filter(d => d.has_redacted_pdf).map(doc => (
            <button
              key={doc.id}
              className="btn btn-secondary btn-sm advisor-doc-btn"
              onClick={() => setViewingDoc(doc)}
            >
              <Eye size={14} />
              {doc.file_name || doc.doc_type}
            </button>
          ))}
        </div>
      )}

      {/* PDF Viewer Modal */}
      {viewingDoc && (
        <PdfViewerModal
          documentId={viewingDoc.id}
          fileName={viewingDoc.file_name}
          onClose={() => setViewingDoc(null)}
        />
      )}

      {/* Flags */}
      {data.flags?.length > 0 && (
        <div className="advisor-flags">
          <AlertTriangle size={16} style={{ color: 'var(--ws-amber)' }} />
          {data.flags.map((flag, i) => (
            <span key={i} className="badge badge-amber">{flag.replace(/_/g, ' ')}</span>
          ))}
        </div>
      )}

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

      {/* Insights list */}
      <h3 className="heading-3" style={{ marginTop: 'var(--space-6)' }}>
        AI Insights ({insights.length})
      </h3>
      {insights.length === 0 ? (
        <EmptyState title="No insights" description="No insights were generated for this case." />
      ) : (
        <div className="advisor-insights-list">
          {insights.map((ins) => (
            <InsightReviewCard
              key={ins.id}
              insight={ins}
              caseId={caseId}
              onUpdate={handleInsightUpdate}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/* ── Queue View ── */
function QueueView({ onSelectCase }) {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('PENDING')

  const load = (status) => {
    setLoading(true)
    getAdvisorQueue(status)
      .then((r) => setList(r.queue || []))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(filter) }, [filter])

  return (
    <>
      {/* Filter tabs */}
      <div className="advisor-filter-tabs">
        {['PENDING', 'APPROVED', 'REJECTED', 'ESCALATED', 'ALL'].map((s) => (
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
      ) : list.length === 0 ? (
        <EmptyState
          icon={Shield}
          title={filter === 'PENDING' ? 'No pending cases' : `No ${filter.toLowerCase()} cases`}
          description={filter === 'PENDING'
            ? 'All cases have been reviewed. New cases appear when analyses are submitted.'
            : 'No cases match this filter.'}
        />
      ) : (
        <div className="advisor-queue-list">
          {list.map((c) => (
            <div
              key={c.case_id}
              className="advisor-queue-card"
              onClick={() => onSelectCase?.(c.case_id)}
            >
              <div className="advisor-queue-card-top">
                <div className="advisor-queue-card-id">
                  <Shield size={16} />
                  Case #{c.case_id}
                </div>
                <span
                  className="advisor-status-badge"
                  style={{ backgroundColor: STATUS_COLORS[c.status] || 'var(--ws-grey-400)' }}
                >
                  {c.status}
                </span>
              </div>
              <div className="advisor-queue-card-info">
                <span><User size={12} /> {c.user_name || c.user_email || 'Unknown'}</span>
                <span>{c.tax_year} — {c.province}</span>
                <span>{fmt(c.income)} income</span>
                <span>{Math.round((c.confidence_score ?? 0) * 100)}% confidence</span>
                <span>{c.insight_count} insight{c.insight_count !== 1 ? 's' : ''}</span>
              </div>
              {c.flags?.length > 0 && (
                <div className="advisor-queue-card-flags">
                  {c.flags.map((flag, i) => (
                    <span key={i} className="badge badge-amber" style={{ fontSize: 'var(--text-xs)' }}>
                      <AlertTriangle size={10} /> {flag.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              )}
              <ChevronRight size={18} className="advisor-queue-chevron" />
            </div>
          ))}
        </div>
      )}
    </>
  )
}

/* ── Main Page ── */
export default function AdvisorDashboard() {
  const [selectedCaseId, setSelectedCaseId] = useState(null)

  return (
    <div className="page-container animate-fade-in">
      {!selectedCaseId && (
        <div className="page-header">
          <div className="page-header-text">
            <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Shield size={24} />
              Advisor Review Queue
            </h1>
            <p className="page-subtitle">
              Review AI-generated insights, add feedback, and approve or reject before delivery to clients.
            </p>
          </div>
        </div>
      )}
      {selectedCaseId ? (
        <CaseDetailView caseId={selectedCaseId} onBack={() => setSelectedCaseId(null)} />
      ) : (
        <QueueView onSelectCase={setSelectedCaseId} />
      )}
    </div>
  )
}
