import { useState, useEffect } from 'react'
import { FlaskConical, ChevronDown, ArrowRight, TrendingDown, TrendingUp, DollarSign } from 'lucide-react'
import { PageLoading, LoadingSpinner } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import FormattedText from '../components/FormattedText'
import { getUserDocuments, runScenario } from '../services/api'
import '../styles/dashboard.css'

const SCENARIOS = [
  { type: 'rrsp_contribution', label: 'RRSP Contribution', desc: 'See how much tax you save', unit: '$', min: 0, max: 50000, step: 500, default: 5000 },
  { type: 'tfsa_contribution', label: 'TFSA Contribution', desc: 'Tax-free growth projection', unit: '$', min: 0, max: 7000, step: 500, default: 3000 },
  { type: 'fhsa_contribution', label: 'FHSA Contribution', desc: 'First Home Savings Account', unit: '$', min: 0, max: 8000, step: 500, default: 4000 },
  { type: 'income_change', label: 'Income Change', desc: 'What if your income changes?', unit: '$', min: 0, max: 300000, step: 5000, default: 80000 },
  { type: 'province_change', label: 'Province Move', desc: 'Compare taxes by province', unit: 'province', provinces: ['ON', 'BC', 'AB', 'QC', 'MB', 'SK', 'NS', 'NB', 'NL', 'PE', 'NT', 'NU', 'YT'] },
]

function CompareCard({ label, current, projected, isCurrency, isPercent }) {
  const currentVal = current || 0
  const projectedVal = projected || 0
  const delta = projectedVal - currentVal
  const improved = isCurrency ? delta < 0 : delta < 0

  const formatValue = (v) => {
    if (isPercent) return `${(v * 100).toFixed(1)}%`
    if (isCurrency) return `$${Number(v).toLocaleString('en-CA', { minimumFractionDigits: 2 })}`
    return String(v)
  }

  return (
    <div className="compare-card">
      <div className="compare-card-label">{label}</div>
      <div className="compare-card-row">
        <div className="compare-card-value">{formatValue(currentVal)}</div>
        <ArrowRight size={16} className="compare-card-arrow" />
        <div className={`compare-card-value ${improved ? 'text-green' : delta > 0 ? 'text-red' : ''}`}>
          {formatValue(projectedVal)}
        </div>
      </div>
      {delta !== 0 && (
        <div className={`compare-card-delta ${improved ? 'text-green' : 'text-red'}`}>
          {improved ? <TrendingDown size={12} /> : <TrendingUp size={12} />}
          {isCurrency && (delta < 0 ? '-' : '+')}{formatValue(Math.abs(delta))}
        </div>
      )}
    </div>
  )
}

export default function Simulator() {
  const [profiles, setProfiles] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedScenario, setSelectedScenario] = useState(null)
  const [value, setValue] = useState(5000)
  const [provinceValue, setProvinceValue] = useState('AB')
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

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

  const handleScenarioSelect = (scenario) => {
    setSelectedScenario(scenario)
    setResult(null)
    setError(null)
    if (scenario.default) setValue(scenario.default)
  }

  const handleRun = async () => {
    if (!selectedId || !selectedScenario) return
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const scenarioValue = selectedScenario.unit === 'province' ? provinceValue : value
      const res = await runScenario(selectedId, selectedScenario.type, scenarioValue)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <PageLoading />

  if (profiles.length === 0) {
    return (
      <div className="page-container">
        <EmptyState
          icon={FlaskConical}
          title="No profiles yet"
          description="Upload a document and run an analysis before using the simulator."
        />
      </div>
    )
  }

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">What-If Simulator</h1>
          <p className="page-subtitle">
            Explore tax scenarios and see the impact instantly
          </p>
        </div>
        {profiles.length > 0 && (
          <div className="dashboard-select-wrap">
            <select
              className="dashboard-select"
              value={selectedId || ''}
              onChange={(e) => { setSelectedId(Number(e.target.value)); setResult(null) }}
            >
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.tax_year || 'N/A'} · {p.province || 'N/A'}{p.file_name ? ` — ${p.file_name}` : ''}
                </option>
              ))}
            </select>
            <ChevronDown size={16} className="dashboard-select-icon" />
          </div>
        )}
      </div>

      {/* Scenario selector */}
      <div className="scenario-grid">
        {SCENARIOS.map((s) => (
          <button
            key={s.type}
            className={`scenario-btn ${selectedScenario?.type === s.type ? 'scenario-btn-active' : ''}`}
            onClick={() => handleScenarioSelect(s)}
          >
            <div className="scenario-btn-label">{s.label}</div>
            <div className="scenario-btn-desc">{s.desc}</div>
          </button>
        ))}
      </div>

      {/* Input form */}
      {selectedScenario && (
        <div className="card" style={{ marginTop: 'var(--space-4)', padding: 'var(--space-6)' }}>
          <h3 style={{ margin: '0 0 var(--space-4)' }}>{selectedScenario.label}</h3>

          {selectedScenario.unit === 'province' ? (
            <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
              <label style={{ fontWeight: 'var(--font-semibold)' }}>Move to:</label>
              <div className="dashboard-select-wrap">
                <select
                  className="dashboard-select"
                  value={provinceValue}
                  onChange={(e) => setProvinceValue(e.target.value)}
                >
                  {selectedScenario.provinces.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
                <ChevronDown size={16} className="dashboard-select-icon" />
              </div>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
                <label style={{ fontWeight: 'var(--font-semibold)' }}>Amount:</label>
                <input
                  type="number"
                  className="simulator-input"
                  value={value}
                  onChange={(e) => setValue(Number(e.target.value))}
                  min={selectedScenario.min}
                  max={selectedScenario.max}
                  step={selectedScenario.step}
                />
              </div>
              <input
                type="range"
                className="simulator-slider"
                value={value}
                onChange={(e) => setValue(Number(e.target.value))}
                min={selectedScenario.min}
                max={selectedScenario.max}
                step={selectedScenario.step}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--ws-grey-500)' }}>
                <span>${selectedScenario.min.toLocaleString()}</span>
                <span>${selectedScenario.max.toLocaleString()}</span>
              </div>
            </div>
          )}

          <button
            onClick={handleRun}
            disabled={running}
            className="btn btn-primary"
            style={{ marginTop: 'var(--space-4)' }}
          >
            {running ? <><LoadingSpinner size={14} /> Calculating...</> : <><FlaskConical size={16} /> Calculate Impact</>}
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="error-banner" style={{ marginTop: 'var(--space-4)' }}>
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="animate-fade-in-up" style={{ marginTop: 'var(--space-6)' }}>
          {/* Tax savings highlight */}
          {result.impact?.tax_savings > 0 && (
            <div className="savings-highlight">
              <DollarSign size={24} />
              <div>
                <div className="savings-highlight-label">Tax Savings</div>
                <div className="savings-highlight-value">
                  ${Number(result.impact.tax_savings).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>
          )}

          {/* TFSA growth projections */}
          {result.scenario_type === 'tfsa_contribution' && result.impact && (
            <div className="summary-grid" style={{ marginBottom: 'var(--space-4)' }}>
              <div className="summary-card">
                <div className="summary-card-label">5-Year Growth</div>
                <div className="summary-card-value text-green">
                  ${Number(result.impact.tax_free_growth_5yr || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-card-label">10-Year Growth</div>
                <div className="summary-card-value text-green">
                  ${Number(result.impact.tax_free_growth_10yr || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-card-label">20-Year Growth</div>
                <div className="summary-card-value text-green">
                  ${Number(result.impact.tax_free_growth_20yr || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>
          )}

          {/* Before / After comparison */}
          {result.current && result.projected && result.scenario_type !== 'tfsa_contribution' && (
            <div className="compare-grid">
              <CompareCard label="Taxable Income" current={result.current.income} projected={result.projected.income} isCurrency />
              <CompareCard label="Tax Liability" current={result.current.tax_liability} projected={result.projected.tax_liability} isCurrency />
              <CompareCard label="Marginal Rate" current={result.current.marginal_rate} projected={result.projected.marginal_rate} isPercent />
            </div>
          )}

          {/* AI Explanation */}
          {result.explanation && (
            <div className="card" style={{ marginTop: 'var(--space-4)', padding: 'var(--space-5)' }}>
              <FormattedText text={result.explanation} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
