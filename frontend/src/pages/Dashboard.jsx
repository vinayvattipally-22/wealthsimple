import { useState, useEffect } from 'react'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { DollarSign, Receipt, TrendingUp, Percent, LayoutDashboard, AlertTriangle, ChevronDown, AlertCircle, Info, ShieldAlert } from 'lucide-react'
import { getUserDashboard, getAnomalies } from '../services/api'
import { PageLoading } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import ReviewPendingBanner from '../components/ReviewPendingBanner'
import { usePageData } from '../context/PageDataContext'
import '../styles/dashboard.css'

const COLORS = ['#dc2626', '#d97706', '#16a34a', '#0d3b66']
const CATEGORY_COLORS = { ACT_NOW: '#dc2626', THIS_YEAR: '#d97706', LONG_TERM: '#16a34a' }

function VerticalTick({ x, y, payload }) {
  return (
    <g transform={`translate(${x},${y + 8})`}>
      <text
        x={0}
        y={0}
        textAnchor="end"
        fill="#737373"
        fontSize={11}
        transform="rotate(-90)"
      >
        {payload.value}
      </text>
    </g>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{label}</div>
      {payload.map((item, i) => (
        <div key={i} className="chart-tooltip-item">
          <span className="chart-tooltip-dot" style={{ background: item.color || item.payload?.fill }} />
          <span>${Number(item.value).toLocaleString('en-CA', { minimumFractionDigits: 2 })}</span>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [selectedId, setSelectedId] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [anomalies, setAnomalies] = useState([])
  const { setPageData } = usePageData()

  // Auto-select the first profile once data loads (no "All Reports" mode)
  useEffect(() => {
    setLoading(true)
    setError(null)
    getUserDashboard(selectedId)
      .then((res) => {
        setData(res)
        setPageData({ page: 'dashboard', data: res })
        // If no profile selected yet, default to first available
        if (!selectedId && res.profiles && res.profiles.length > 0) {
          setSelectedId(res.profiles[0].id)
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedId, setPageData])

  useEffect(() => {
    if (!selectedId) return
    getAnomalies(selectedId)
      .then((res) => setAnomalies(res.anomalies || []))
      .catch(() => setAnomalies([]))
  }, [selectedId])

  if (loading) return <PageLoading />

  if (error) {
    return (
      <div className="page-container">
        <div className="error-banner">
          <AlertTriangle size={20} className="banner-icon" />
          {error}
        </div>
      </div>
    )
  }

  if (!data || (data.profiles && data.profiles.length === 0)) {
    return (
      <div className="page-container">
        <EmptyState
          icon={LayoutDashboard}
          title="No reports yet"
          description="Upload a document from My Documents and run an analysis to see your dashboard."
        />
      </div>
    )
  }

  const pieData = Object.entries(data.insights_by_category || {})
    .filter(([, items]) => items.length > 0)
    .map(([cat, items]) => ({
      name: cat.replace('_', ' '),
      value: items.reduce((s, i) => s + (i.estimated_value || 0), 0),
    }))

  const barData = (data.chart_data || []).map(d => ({
    name: (d.name || '').replace(/_/g, ' ').substring(0, 20),
    value: d.value || 0,
    fill: CATEGORY_COLORS[d.category] || '#0d3b66',
  }))

  const confidence = data.confidence || 0
  const confColor = confidence >= 0.85 ? 'var(--ws-green)' : confidence >= 0.7 ? 'var(--ws-amber)' : 'var(--ws-red)'

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">{data.tax_year || ''}</p>
        </div>
        {data.profiles && data.profiles.length > 1 && (
          <div className="dashboard-select-wrap">
            <select
              className="dashboard-select"
              value={selectedId || ''}
              onChange={(e) => setSelectedId(Number(e.target.value))}
            >
              {data.profiles.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
            <ChevronDown size={16} className="dashboard-select-icon" />
          </div>
        )}
      </div>

      {data.review_pending && (
        <ReviewPendingBanner message="Your AI-generated insights are under advisor review. Savings and chart data will update once insights are approved." />
      )}

      {anomalies.length > 0 && (
        <div className="anomaly-section" style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
            <ShieldAlert size={18} style={{ color: 'var(--ws-amber)' }} />
            <h3 style={{ margin: 0, fontSize: '0.95rem' }}>AI Anomaly Detection</h3>
          </div>
          {anomalies.map((a, i) => {
            const sevConfig = {
              critical: { color: 'var(--ws-red)', bg: '#fef2f2', icon: AlertCircle },
              warning: { color: 'var(--ws-amber)', bg: '#fffbeb', icon: AlertTriangle },
              info: { color: 'var(--ws-blue)', bg: '#eff6ff', icon: Info },
            }
            const cfg = sevConfig[a.severity] || sevConfig.info
            const SevIcon = cfg.icon
            return (
              <div
                key={i}
                className="anomaly-card"
                style={{
                  background: cfg.bg,
                  borderLeft: `3px solid ${cfg.color}`,
                  padding: 'var(--space-3) var(--space-4)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)' }}>
                  <SevIcon size={16} style={{ color: cfg.color, marginTop: 2, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', color: cfg.color, textTransform: 'uppercase', marginBottom: 2 }}>
                      {a.severity}
                    </div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 500 }}>{a.message}</div>
                    {a.suggestion && (
                      <div style={{ fontSize: '0.82rem', color: 'var(--ws-grey-500)', marginTop: 4 }}>{a.suggestion}</div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="summary-cards">
        <div className="summary-card">
          <div className="summary-card-icon blue"><DollarSign size={20} /></div>
          <div className="label">Employment Income</div>
          <div className="value">${(data.income || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-icon red"><Receipt size={20} /></div>
          <div className="label">Tax Liability</div>
          <div className="value red">${(data.tax_liability || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-icon green"><TrendingUp size={20} /></div>
          <div className="label">Total Savings Found{data.review_pending ? ' (under review)' : ''}</div>
          <div className="value green">${(data.total_savings || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-icon amber"><Percent size={20} /></div>
          <div className="label">Marginal Rate</div>
          <div className="value">
            {data.marginal_rate != null
              ? `${(data.marginal_rate * 100).toFixed(1)}%`
              : '—'}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 'var(--space-8)' }}>
        <div className="label" style={{ marginBottom: 'var(--space-3)' }}>Analysis Confidence</div>
        <div className="confidence-meter">
          <div className="confidence-bar">
            <div
              className="confidence-fill"
              style={{ width: `${confidence * 100}%`, background: confColor }}
            />
          </div>
          <div className="confidence-label">
            <span>{confidence >= 0.85 ? 'High confidence' : confidence >= 0.7 ? 'Moderate confidence' : 'Low confidence'}</span>
            <span style={{ fontWeight: 600, color: confColor }}>{(confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Savings by Insight</h3>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={barData} margin={{ bottom: 10 }}>
                <XAxis dataKey="name" tick={<VerticalTick />} height={140} interval={0} />
                <YAxis fontSize={11} tick={{ fill: '#737373' }} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-muted">No insights data available</p>}
        </div>

        <div className="chart-card">
          <h3>Savings by Category</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={55}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  verticalAlign="bottom"
                  formatter={(value, entry) => {
                    const item = pieData.find(d => d.name === value)
                    return `${value}: $${item ? item.value.toLocaleString('en-CA', { minimumFractionDigits: 0 }) : '0'}`
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-muted">No category data available</p>}
        </div>
      </div>
    </div>
  )
}
