import { useState, useEffect } from 'react'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { DollarSign, Receipt, TrendingUp, Percent, LayoutDashboard, AlertTriangle, ChevronDown } from 'lucide-react'
import { getUserDashboard } from '../services/api'
import { PageLoading } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import '../styles/dashboard.css'

const COLORS = ['#dc2626', '#d97706', '#16a34a', '#0d3b66']
const CATEGORY_COLORS = { ACT_NOW: '#dc2626', THIS_YEAR: '#d97706', LONG_TERM: '#16a34a' }

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

  useEffect(() => {
    setLoading(true)
    setError(null)
    getUserDashboard(selectedId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
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

  const isCumulative = data.mode === 'cumulative'

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
          <p className="page-subtitle">
            {isCumulative
              ? `All reports${data.tax_year ? ` · ${data.tax_year}` : ''}`
              : `${data.tax_year || ''}${data.province ? ` · ${data.province}` : ''}`
            }
          </p>
        </div>
        {data.profiles && data.profiles.length > 0 && (
          <div className="dashboard-select-wrap">
            <select
              className="dashboard-select"
              value={selectedId || ''}
              onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">All Reports</option>
              {data.profiles.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
            <ChevronDown size={16} className="dashboard-select-icon" />
          </div>
        )}
      </div>

      <div className="summary-cards">
        <div className="summary-card">
          <div className="summary-card-icon blue"><DollarSign size={20} /></div>
          <div className="label">{isCumulative ? 'Total Income' : 'Employment Income'}</div>
          <div className="value">${(data.income || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-icon red"><Receipt size={20} /></div>
          <div className="label">{isCumulative ? 'Total Tax Liability' : 'Tax Liability'}</div>
          <div className="value red">${(data.tax_liability || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-icon green"><TrendingUp size={20} /></div>
          <div className="label">Total Savings Found</div>
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
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData}>
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} fontSize={11} tick={{ fill: '#737373' }} />
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
                  outerRadius={100}
                  innerRadius={60}
                  paddingAngle={3}
                  label={({ name, value }) => `${name}: $${value.toFixed(0)}`}
                  dataKey="value"
                >
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-muted">No category data available</p>}
        </div>
      </div>
    </div>
  )
}
