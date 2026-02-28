import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import FormattedText from './FormattedText'
import '../styles/dashboard.css'

export default function InsightCard({ insight }) {
  const [expanded, setExpanded] = useState(false)

  if (!insight) return null
  const category = insight.category || 'THIS_YEAR'
  const color =
    category === 'ACT_NOW' ? '#c00' :
    category === 'THIS_YEAR' ? '#b8860b' : '#228b22'

  const priority = (insight.priority || 'MEDIUM').toLowerCase()

  return (
    <div
      className="card insight-card animate-fade-in"
      style={{ borderLeft: `4px solid ${color}` }}
    >
      <div className="insight-header">
        <span className={`badge badge-${priority}`}>{insight.priority || 'MEDIUM'}</span>
        <span
          className="insight-expand"
          onClick={() => setExpanded(!expanded)}
        >
          {insight.headline}
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </div>

      {expanded && insight.detail && (
        <div className="insight-detail">
          <FormattedText text={insight.detail} />
        </div>
      )}

      {insight.estimated_value != null && (
        <div className="insight-value">
          Estimated value: ${Number(insight.estimated_value).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
        </div>
      )}

      {expanded && insight.calculation_shown && (
        <div className="calc-block">{insight.calculation_shown}</div>
      )}

      {expanded && insight.action_required && (
        <p className="insight-action">{insight.action_required}</p>
      )}

    </div>
  )
}
