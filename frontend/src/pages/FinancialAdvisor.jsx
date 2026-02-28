import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  BrainCircuit, ChevronDown, Heart, TrendingUp, Shield,
  Calendar, Clock, AlertTriangle, CheckCircle2, ArrowRight,
  ListChecks, FlaskConical, MessageCircle, DollarSign,
  PiggyBank, Target,
} from 'lucide-react'
import { getAdvisorData } from '../services/api'
import EmptyState from '../components/EmptyState'
import { LoadingSpinner } from '../components/LoadingState'
import '../styles/dashboard.css'

function HealthGauge({ score }) {
  const overall = score?.overall || 0
  const radius = 54
  const circumference = 2 * Math.PI * radius
  const progress = (overall / 100) * circumference
  const color = overall >= 70 ? 'var(--ws-green)' : overall >= 40 ? 'var(--ws-amber)' : 'var(--ws-red)'

  return (
    <div className="health-gauge">
      <svg viewBox="0 0 120 120" className="health-gauge-svg">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--ws-grey-100)" strokeWidth="8" />
        <circle
          cx="60" cy="60" r={radius} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={circumference - progress}
          strokeLinecap="round" transform="rotate(-90 60 60)"
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
      </svg>
      <div className="health-gauge-value">
        <span className="health-gauge-number" style={{ color }}>{Math.round(overall)}</span>
        <span className="health-gauge-label">/ 100</span>
      </div>
    </div>
  )
}

function ComponentBar({ label, value, icon: Icon }) {
  const color = value >= 70 ? 'var(--ws-green)' : value >= 40 ? 'var(--ws-amber)' : 'var(--ws-red)'
  return (
    <div className="health-component">
      <div className="health-component-label">
        <Icon size={14} />
        <span>{label}</span>
        <span className="health-component-value">{Math.round(value)}%</span>
      </div>
      <div className="health-component-bar">
        <div className="health-component-fill" style={{ width: `${value}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}

function YearCompareCard({ title, year, items, accent }) {
  return (
    <div className={`year-compare-card year-compare-${accent}`}>
      <div className="year-compare-header">
        <span className="year-compare-title">{title}</span>
        <span className="year-compare-year">{year}</span>
      </div>
      <div className="year-compare-items">
        {items.map((item, i) => (
          <div key={i} className="year-compare-item">
            <span className="year-compare-item-label">{item.label}</span>
            <span className="year-compare-item-value">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function RecommendationCard({ rec }) {
  const urgencyColors = {
    ACT_NOW: 'var(--ws-red)',
    THIS_YEAR: 'var(--ws-blue)',
    LONG_TERM: 'var(--ws-grey-400)',
  }
  return (
    <div className="recommendation-card animate-fade-in-up">
      <div className="recommendation-last-year">
        <Clock size={14} />
        <span>{rec.last_year}</span>
      </div>
      <div className="recommendation-this-year">
        <ArrowRight size={16} />
        <span>{rec.this_year}</span>
      </div>
      <div className="recommendation-footer">
        {rec.deadline && (
          <span className="recommendation-deadline" style={{ borderColor: urgencyColors[rec.urgency] || 'var(--ws-blue)' }}>
            <Calendar size={12} />
            {new Date(rec.deadline).toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
        )}
        {rec.estimated_value > 0 && (
          <span className="recommendation-value">
            +${Number(rec.estimated_value).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
          </span>
        )}
        <span className={`badge badge-${rec.priority === 'HIGH' ? 'red' : rec.priority === 'MEDIUM' ? 'amber' : 'grey'}`}>
          {rec.priority}
        </span>
      </div>
    </div>
  )
}

function CalendarTimeline({ calendar }) {
  if (!calendar || calendar.length === 0) return null
  return (
    <div className="financial-calendar">
      <div className="calendar-track">
        {calendar.map((item, i) => (
          <div
            key={i}
            className={`calendar-item calendar-item-${item.urgency}`}
            title={`${item.label} — ${item.date}`}
          >
            <div className="calendar-dot" />
            <div className="calendar-info">
              <span className="calendar-month">{item.month} {item.day}</span>
              <span className="calendar-label">{item.label}</span>
              {item.days_away != null && (
                <span className="calendar-days">
                  {item.days_away === 0 ? 'Today' : `${item.days_away}d`}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const fmt = (v) => `$${Number(v || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}`
const pct = (v) => `${(Number(v || 0) * 100).toFixed(1)}%`

export default function FinancialAdvisor() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState(null)

  const load = (profileId) => {
    setLoading(true)
    getAdvisorData(profileId)
      .then((res) => {
        setData(res)
        if (!selectedId && res.selected_profile_id) {
          setSelectedId(res.selected_profile_id)
        }
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(null) }, [])

  const handleProfileChange = (newId) => {
    setSelectedId(newId)
    load(newId)
  }

  if (loading) {
    return (
      <div className="page-container" style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-8)' }}>
        <LoadingSpinner size={24} />
      </div>
    )
  }

  if (!data || !data.last_year || !data.last_year.income) {
    return (
      <div className="page-container">
        <EmptyState
          icon={BrainCircuit}
          title="No financial data yet"
          description="Upload a document and run analysis first to get your AI Financial Advisor insights."
        />
      </div>
    )
  }

  const { health_score, last_year, this_year, recommendations, calendar, profiles } = data
  const components = health_score?.components || {}

  return (
    <div className="page-container" style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* Header */}
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <BrainCircuit size={24} />
            AI Financial Advisor
          </h1>
          <p className="page-subtitle">Your personalized financial strategy based on {last_year.tax_year} data</p>
        </div>
        {profiles && profiles.length > 1 && (
          <div className="dashboard-select-wrap">
            <select
              className="dashboard-select"
              value={selectedId || ''}
              onChange={(e) => handleProfileChange(Number(e.target.value))}
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
            <ChevronDown size={16} className="dashboard-select-icon" />
          </div>
        )}
      </div>

      {/* Health Score + Components */}
      <div className="advisor-health-section">
        <div className="advisor-health-gauge-wrap">
          <h2 className="heading-3">Financial Health</h2>
          <HealthGauge score={health_score} />
        </div>
        <div className="advisor-health-components">
          <ComponentBar label="RRSP Utilization" value={components.rrsp_utilization || 0} icon={PiggyBank} />
          <ComponentBar label="TFSA Utilization" value={components.tfsa_utilization || 0} icon={DollarSign} />
          <ComponentBar label="Tax Efficiency" value={components.tax_efficiency || 0} icon={TrendingUp} />
          <ComponentBar label="Action Completion" value={components.action_completion || 0} icon={Target} />
        </div>
      </div>

      {/* Last Year vs This Year */}
      <div className="year-compare-grid">
        <YearCompareCard
          title={`${last_year.tax_year} Summary`}
          year="Last Year"
          accent="past"
          items={[
            { label: 'Income', value: fmt(last_year.income) },
            { label: 'Tax Paid', value: fmt(last_year.tax_paid) },
            { label: 'Effective Rate', value: pct(last_year.effective_rate) },
            { label: 'RRSP Contributed', value: fmt(last_year.rrsp_contributed) },
            { label: 'RRSP Room Left', value: fmt(last_year.rrsp_room_remaining) },
            { label: 'TFSA Room Left', value: fmt(last_year.tfsa_room_remaining) },
            { label: 'Refund / Owing', value: fmt(last_year.refund_or_owing) },
          ]}
        />
        <YearCompareCard
          title={`${this_year.current_year} Plan`}
          year="This Year"
          accent="future"
          items={[
            { label: 'Savings Opportunity', value: fmt(this_year.total_savings_opportunity) },
            { label: 'Pending Actions', value: String(this_year.pending_actions) },
            { label: 'Completed Actions', value: `${this_year.completed_actions} / ${this_year.total_actions}` },
            ...(this_year.next_deadline ? [{
              label: 'Next Deadline',
              value: `${this_year.next_deadline.label} (${this_year.next_deadline.days_away}d)`,
            }] : []),
          ]}
        />
      </div>

      {/* Financial Calendar */}
      {calendar && calendar.length > 0 && (
        <div className="advisor-section">
          <h2 className="heading-3" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Calendar size={18} />
            Financial Calendar — {this_year.current_year}
          </h2>
          <CalendarTimeline calendar={calendar} />
        </div>
      )}

      {/* Top Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div className="advisor-section">
          <h2 className="heading-3" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <TrendingUp size={18} />
            Top Recommendations
          </h2>
          <div className="recommendations-list">
            {recommendations.map((rec, i) => (
              <RecommendationCard key={i} rec={rec} />
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="advisor-quick-actions">
        <Link to="/simulator" className="btn btn-primary">
          <FlaskConical size={16} />
          Run Simulator
        </Link>
        <Link to="/actions" className="btn btn-success">
          <ListChecks size={16} />
          View Action Items
        </Link>
        <button
          className="btn btn-secondary"
          onClick={() => {
            const chatBtn = document.querySelector('.chat-widget-toggle')
            if (chatBtn) chatBtn.click()
          }}
        >
          <MessageCircle size={16} />
          Ask Copilot
        </button>
      </div>
    </div>
  )
}
