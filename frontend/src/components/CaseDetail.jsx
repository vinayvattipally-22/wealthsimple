import { useState, useEffect } from 'react'
import { ChevronLeft, Check, X, AlertTriangle } from 'lucide-react'
import InsightCard from './InsightCard'
import { LoadingSpinner } from './LoadingState'
import EmptyState from './EmptyState'
import { getCase, approveCase, rejectCase, escalateCase } from '../services/api'

const STATUS_BADGE = {
  PENDING: 'badge-medium',
  APPROVED: 'badge-low',
  REJECTED: 'badge-high',
  ESCALATED: 'badge-info',
}

export default function CaseDetail({ caseId, onBack }) {
  const [caseData, setCaseData] = useState(null)
  const [loading, setLoading] = useState(!!caseId)
  const [action, setAction] = useState(null)

  useEffect(() => {
    if (!caseId) return
    setLoading(true)
    getCase(caseId).then(setCaseData).finally(() => setLoading(false))
  }, [caseId])

  const doApprove = () => {
    setAction('approving')
    approveCase(caseId).then(() => { setCaseData((c) => c ? { ...c, status: 'APPROVED' } : c) }).finally(() => setAction(null))
  }
  const doReject = () => {
    setAction('rejecting')
    rejectCase(caseId).then(() => { setCaseData((c) => c ? { ...c, status: 'REJECTED' } : c) }).finally(() => setAction(null))
  }
  const doEscalate = () => {
    setAction('escalating')
    escalateCase(caseId).then(() => { setCaseData((c) => c ? { ...c, status: 'ESCALATED' } : c) }).finally(() => setAction(null))
  }

  if (!caseId) return null

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 'var(--space-8)', justifyContent: 'center' }}>
        <LoadingSpinner />
        <span className="text-muted">Loading case...</span>
      </div>
    )
  }

  if (!caseData) {
    return <EmptyState title="Case not found" description="This case could not be loaded." />
  }

  const insights = caseData.insights ?? []
  const status = caseData.status

  return (
    <div className="animate-fade-in">
      <div className="case-header">
        <div className="case-header-left">
          <button className="btn btn-ghost btn-sm" onClick={onBack}>
            <ChevronLeft size={16} /> Back
          </button>
          <span className="heading-2" style={{ margin: 0 }}>Case #{caseId}</span>
          <span className={`badge ${STATUS_BADGE[status] || 'badge-neutral'}`}>{status}</span>
        </div>
        {status === 'PENDING' && (
          <div className="case-actions">
            <button className="btn btn-success btn-sm" onClick={doApprove} disabled={!!action}>
              <Check size={14} /> Approve All
            </button>
            <button className="btn btn-danger btn-sm" onClick={doReject} disabled={!!action}>
              <X size={14} /> Reject
            </button>
            <button className="btn btn-secondary btn-sm" onClick={doEscalate} disabled={!!action}>
              <AlertTriangle size={14} /> Escalate
            </button>
            {action && <LoadingSpinner size={16} />}
          </div>
        )}
      </div>

      <div className="case-info-grid">
        <div className="case-info-item">
          <div className="case-info-label">Confidence</div>
          <div className="case-info-value">{Math.round((caseData.confidence_score ?? 0) * 100)}%</div>
        </div>
        <div className="case-info-item">
          <div className="case-info-label">Insights</div>
          <div className="case-info-value">{insights.length}</div>
        </div>
        {caseData.flags?.length > 0 && (
          <div className="case-info-item">
            <div className="case-info-label">Flags</div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', marginTop: 'var(--space-1)' }}>
              {caseData.flags.map((flag, i) => (
                <span key={i} className="badge badge-medium">{flag}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      <h3 className="heading-3">Insights</h3>
      {insights.length === 0 ? (
        <EmptyState title="No insights" description="No insights were generated for this case." />
      ) : (
        insights.map((ins) => (
          <InsightCard key={ins.id} insight={ins} />
        ))
      )}
    </div>
  )
}
