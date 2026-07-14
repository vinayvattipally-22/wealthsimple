import { useState, useEffect } from 'react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, Percent, AlertTriangle, ChevronDown } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getTrends } from '../services/api'
import { PageLoading } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { usePageData } from '../context/PageDataContext'
import '../styles/dashboard.css'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{label}</div>
      {payload.map((item, i) => (
        <div key={i} className="chart-tooltip-item">
          <span className="chart-tooltip-dot" style={{ background: item.color }} />
          <span>{item.name}: ${Number(item.value).toLocaleString('en-CA')}</span>
        </div>
      ))}
    </div>
  )
}

export default function Trends() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [yearFrom, setYearFrom] = useState(null)
  const [yearTo, setYearTo] = useState(null)
  const { setPageData } = usePageData()

  useEffect(() => {
    if (!user?.id) { setLoading(false); return }
    setLoading(true)
    getTrends(user.id)
      .then((res) => {
        setData(res)
        setPageData({ page: 'trends', data: res })
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [user, setPageData])

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

  if (!data || !data.years || data.years.length === 0) {
    return (
      <div className="page-container">
        <EmptyState
          icon={TrendingUp}
          title="No trend data available"
          description="Upload T4s for multiple tax years to see income trends, tax comparisons, and savings over time."
        />
      </div>
    )
  }

  const allChartData = data.years.map((year, i) => ({
    year,
    income: data.income[i],
    tax: data.tax_paid[i],
    effectiveRate: (data.effective_rate[i] * 100),
    savings: data.savings[i],
    growth: data.yoy_growth[i],
  }))

  const allYears = data.years
  const fromYear = yearFrom || allYears[0]
  const toYear = yearTo || allYears[allYears.length - 1]
  const chartData = allChartData.filter(d => d.year >= fromYear && d.year <= toYear)

  const latest = chartData[chartData.length - 1]
  const previous = chartData.length > 1 ? chartData[chartData.length - 2] : null
  const incomeUp = previous ? latest.income > previous.income : true

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">Multi-Year Trends</h1>
          <p className="page-subtitle">{fromYear} &ndash; {toYear}</p>
        </div>
        {allYears.length > 1 && (
          <div className="trends-year-range">
            <div className="dashboard-select-wrap">
              <select
                className="dashboard-select"
                value={fromYear}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  setYearFrom(v)
                  if (v > toYear) setYearTo(v)
                }}
              >
                {allYears.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
              <ChevronDown size={16} className="dashboard-select-icon" />
            </div>
            <span className="trends-year-range-sep">to</span>
            <div className="dashboard-select-wrap">
              <select
                className="dashboard-select"
                value={toYear}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  setYearTo(v)
                  if (v < fromYear) setYearFrom(v)
                }}
              >
                {allYears.filter(y => y >= fromYear).map(y => <option key={y} value={y}>{y}</option>)}
              </select>
              <ChevronDown size={16} className="dashboard-select-icon" />
            </div>
          </div>
        )}
      </div>

      {previous && (
        <div className="summary-cards">
          <div className="summary-card">
            <div className="summary-card-icon" style={{ background: incomeUp ? 'var(--ws-green-light)' : 'var(--ws-red-light)', color: incomeUp ? 'var(--ws-green)' : 'var(--ws-red)' }}>
              {incomeUp ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
            </div>
            <div className="label">Income Change</div>
            <div className={`value ${incomeUp ? 'green' : 'red'}`}>
              {latest.growth != null ? `${latest.growth > 0 ? '+' : ''}${latest.growth}%` : 'N/A'}
            </div>
            <span className="text-muted">{previous.year} to {latest.year}</span>
          </div>
          <div className="summary-card">
            <div className="summary-card-icon blue"><DollarSign size={20} /></div>
            <div className="label">Latest Income</div>
            <div className="value">${latest.income.toLocaleString('en-CA')}</div>
          </div>
          <div className="summary-card">
            <div className="summary-card-icon amber"><Percent size={20} /></div>
            <div className="label">Effective Tax Rate</div>
            <div className="value">{latest.effectiveRate.toFixed(1)}%</div>
          </div>
          <div className="summary-card">
            <div className="summary-card-icon green"><TrendingUp size={20} /></div>
            <div className="label">Savings Identified</div>
            <div className="value green">${latest.savings.toLocaleString('en-CA')}</div>
          </div>
        </div>
      )}

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Income & Tax Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--ws-grey-200)" />
              <XAxis dataKey="year" tick={{ fill: '#737373' }} />
              <YAxis fontSize={11} tick={{ fill: '#737373' }} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="income" stroke="#0d3b66" strokeWidth={2} name="Income" dot={{ r: 4, fill: '#0d3b66' }} />
              <Line type="monotone" dataKey="tax" stroke="#dc2626" strokeWidth={2} name="Tax Paid" dot={{ r: 4, fill: '#dc2626' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Savings Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--ws-grey-200)" />
              <XAxis dataKey="year" tick={{ fill: '#737373' }} />
              <YAxis fontSize={11} tick={{ fill: '#737373' }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="savings" stroke="#16a34a" fill="rgba(22, 163, 74, 0.15)" strokeWidth={2} name="Savings" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Year-by-Year Summary</h3>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Year</th>
              <th>Income</th>
              <th>Tax</th>
              <th>Eff. Rate</th>
              <th>Savings</th>
              <th>Growth</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((row) => (
              <tr key={row.year}>
                <td className="font-semibold">{row.year}</td>
                <td>${row.income.toLocaleString('en-CA')}</td>
                <td className="text-red">${row.tax.toLocaleString('en-CA')}</td>
                <td>{row.effectiveRate.toFixed(1)}%</td>
                <td className="text-green">${row.savings.toLocaleString('en-CA')}</td>
                <td>{row.growth != null ? `${row.growth > 0 ? '+' : ''}${row.growth}%` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
