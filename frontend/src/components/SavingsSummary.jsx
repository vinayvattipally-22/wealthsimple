import '../styles/dashboard.css'

export default function SavingsSummary({ summary }) {
  if (!summary) return null
  const total = summary.total_identified_savings ?? summary.total_savings ?? 0
  const actNow = summary.act_now_count ?? 0
  const thisYear = summary.this_year_count ?? 0
  const longTerm = summary.long_term_count ?? 0

  return (
    <div className="savings-summary">
      <div className="savings-summary-label">Total identified savings</div>
      <div className="savings-summary-value">
        ${Number(total).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
      </div>
      <div className="savings-categories">
        {actNow > 0 && (
          <span className="savings-category-item">
            <span className="status-dot status-dot-red" />
            {actNow} act now
          </span>
        )}
        {thisYear > 0 && (
          <span className="savings-category-item">
            <span className="status-dot status-dot-amber" />
            {thisYear} this year
          </span>
        )}
        {longTerm > 0 && (
          <span className="savings-category-item">
            <span className="status-dot status-dot-green" />
            {longTerm} long term
          </span>
        )}
      </div>
    </div>
  )
}
