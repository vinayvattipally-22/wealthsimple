import { useState, useEffect } from 'react'
import { FlaskConical, ChevronDown, ArrowRight, TrendingDown, TrendingUp, DollarSign, Sparkles, MessageSquare, Calendar, Send } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { PageLoading, LoadingSpinner } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import FormattedText from '../components/FormattedText'
import { getUserDocuments, runScenario, getScenarioSuggestions, runNaturalLanguageScenario, runMultiYearProjection } from '../services/api'
import { usePageData } from '../context/PageDataContext'
import '../styles/dashboard.css'

const SCENARIOS = [
  { type: 'rrsp_contribution', label: 'RRSP Contribution', desc: 'See how much tax you save', unit: '$', min: 0, max: 50000, step: 500, default: 5000 },
  { type: 'tfsa_contribution', label: 'TFSA Contribution', desc: 'Tax-free growth projection', unit: '$', min: 0, max: 7000, step: 500, default: 3000 },
  { type: 'fhsa_contribution', label: 'FHSA Contribution', desc: 'First Home Savings Account', unit: '$', min: 0, max: 8000, step: 500, default: 4000 },
  { type: 'income_change', label: 'Income Change', desc: 'What if your income changes?', unit: '$', min: 0, max: 300000, step: 5000, default: 80000 },
  { type: 'province_change', label: 'Province Move', desc: 'Compare taxes by province', unit: 'province', provinces: ['ON', 'BC', 'AB', 'QC', 'MB', 'SK', 'NS', 'NB', 'NL', 'PE', 'NT', 'NU', 'YT'] },
]

function CompareCard({ label, current, projected, isCurrency, isPercent, invertColor }) {
  const currentVal = current || 0
  const projectedVal = projected || 0
  const delta = projectedVal - currentVal
  // invertColor: for metrics where increase is good (green), e.g. RRSP room, credits
  const improved = invertColor ? delta > 0 : (isCurrency ? delta < 0 : delta < 0)

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
        <div className={`compare-card-value ${improved ? 'text-green' : delta !== 0 ? 'text-red' : ''}`}>
          {formatValue(projectedVal)}
        </div>
      </div>
      {delta !== 0 && (
        <div className={`compare-card-delta ${improved ? 'text-green' : 'text-red'}`}>
          {improved ? (invertColor ? <TrendingUp size={12} /> : <TrendingDown size={12} />) : (invertColor ? <TrendingDown size={12} /> : <TrendingUp size={12} />)}
          {isCurrency && (delta < 0 ? '-' : '+')}{formatValue(Math.abs(delta))}
        </div>
      )}
    </div>
  )
}

function MultiYearChart({ data }) {
  if (!data?.projections?.length) return null
  const chartData = data.projections.map(p => ({
    name: `Yr ${p.year}`,
    'RRSP Savings': p.rrsp_savings,
    'TFSA Growth': p.tfsa_growth,
    'FHSA Savings': p.fhsa_savings,
  }))
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <XAxis dataKey="name" fontSize={11} tick={{ fill: '#737373' }} />
        <YAxis fontSize={11} tick={{ fill: '#737373' }} />
        <Tooltip
          formatter={(v) => `$${Number(v).toLocaleString('en-CA', { minimumFractionDigits: 0 })}`}
          contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8 }}
        />
        <Legend />
        <Bar dataKey="RRSP Savings" fill="#16a34a" radius={[2, 2, 0, 0]} />
        <Bar dataKey="TFSA Growth" fill="#0d3b66" radius={[2, 2, 0, 0]} />
        <Bar dataKey="FHSA Savings" fill="#d97706" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
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
  const { setPageData } = usePageData()

  // AI features state
  const [suggestions, setSuggestions] = useState([])
  const [nlQuery, setNlQuery] = useState('')
  const [nlRunning, setNlRunning] = useState(false)
  const [nlResults, setNlResults] = useState(null)
  const [multiYear, setMultiYear] = useState(null)
  const [multiYearRunning, setMultiYearRunning] = useState(false)
  const [myRrsp, setMyRrsp] = useState(5000)
  const [myTfsa, setMyTfsa] = useState(7000)
  const [myFhsa, setMyFhsa] = useState(8000)
  const [myYears, setMyYears] = useState(10)

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

  // Load smart suggestions when profile changes
  useEffect(() => {
    if (!selectedId) return
    getScenarioSuggestions(selectedId)
      .then((res) => setSuggestions(res.suggestions || []))
      .catch(() => setSuggestions([]))
  }, [selectedId])

  const handleScenarioSelect = (scenario) => {
    setSelectedScenario(scenario)
    setResult(null)
    setError(null)
    if (scenario.default) setValue(scenario.default)
  }

  const handleSuggestionClick = (suggestion) => {
    const scenario = SCENARIOS.find(s => s.type === suggestion.scenario_type)
    if (scenario) {
      setSelectedScenario(scenario)
      setResult(null)
      setError(null)
      if (suggestion.scenario_type === 'province_change') {
        setProvinceValue(suggestion.suggested_value)
      } else {
        setValue(suggestion.suggested_value)
      }
    }
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
      setPageData({ page: 'simulator', data: { scenario: selectedScenario.type, value: scenarioValue, result: res } })
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  const handleNLRun = async () => {
    if (!selectedId || !nlQuery.trim()) return
    setNlRunning(true)
    setError(null)
    setNlResults(null)
    try {
      const res = await runNaturalLanguageScenario(selectedId, nlQuery)
      if (res.error) {
        setError(res.error)
      } else {
        setNlResults(res)
        if (res.results?.length === 1) {
          setResult(res.results[0])
        }
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setNlRunning(false)
    }
  }

  const handleMultiYear = async () => {
    if (!selectedId) return
    setMultiYearRunning(true)
    try {
      const res = await runMultiYearProjection(selectedId, myYears, myRrsp, myTfsa, myFhsa)
      setMultiYear(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setMultiYearRunning(false)
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
              onChange={(e) => { setSelectedId(Number(e.target.value)); setResult(null); setNlResults(null); setMultiYear(null) }}
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

      {/* AI Smart Suggestions */}
      {suggestions.length > 0 && (
        <div style={{ marginBottom: 'var(--space-5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
            <Sparkles size={16} style={{ color: 'var(--ws-amber)' }} />
            <span style={{ fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)' }}>AI Recommendations</span>
          </div>
          <div className="scenario-grid">
            {suggestions.map((s, i) => (
              <button
                key={i}
                className="scenario-btn"
                onClick={() => handleSuggestionClick(s)}
                style={{ borderLeft: `3px solid ${s.priority === 'HIGH' ? 'var(--ws-green)' : s.priority === 'LOW' ? 'var(--ws-grey-400)' : 'var(--ws-amber)'}` }}
              >
                <div className="scenario-btn-label">{s.title}</div>
                <div className="scenario-btn-desc">{s.description}</div>
                <div style={{ marginTop: 'var(--space-2)', fontWeight: 'var(--font-semibold)', color: 'var(--ws-green)', fontSize: 'var(--text-sm)' }}>
                  ${Number(s.potential_savings).toLocaleString('en-CA', { minimumFractionDigits: 0 })} potential savings
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Natural Language Input */}
      <div className="card" style={{ marginBottom: 'var(--space-4)', padding: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
          <MessageSquare size={16} style={{ color: 'var(--ws-blue)' }} />
          <span style={{ fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)' }}>Ask AI a Scenario</span>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <input
            type="text"
            className="simulator-input"
            style={{ flex: 1 }}
            placeholder="e.g. What if I get a $20K raise and max out my RRSP?"
            value={nlQuery}
            onChange={(e) => setNlQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNLRun()}
          />
          <button
            onClick={handleNLRun}
            disabled={nlRunning || !nlQuery.trim()}
            className="btn btn-primary"
          >
            {nlRunning ? <LoadingSpinner size={14} /> : <Send size={14} />}
          </button>
        </div>
        {nlResults?.parsed?.explanation && (
          <div style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-xs)', color: 'var(--ws-grey-500)' }}>
            Parsed: {nlResults.parsed.explanation}
          </div>
        )}
      </div>

      {/* NL Multi-scenario results */}
      {nlResults?.results?.length > 1 && (
        <div className="animate-fade-in-up" style={{ marginBottom: 'var(--space-4)' }}>
          {nlResults.results.map((r, i) => (
            <div key={i} className="card" style={{ marginBottom: 'var(--space-3)', padding: 'var(--space-4)' }}>
              <h4 style={{ margin: '0 0 var(--space-2)', textTransform: 'capitalize' }}>
                {(r.scenario_type || '').replace(/_/g, ' ')}
              </h4>
              {r.impact?.tax_savings > 0 && (
                <span className="text-green font-semibold">
                  Tax savings: ${Number(r.impact.tax_savings).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </span>
              )}
              {r.explanation && (
                <div style={{ marginTop: 'var(--space-2)' }}>
                  <FormattedText text={r.explanation} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

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
              <div className="summary-card">
                <div className="summary-card-label">Tax Saved vs Taxable (20yr)</div>
                <div className="summary-card-value text-green">
                  ${Number(result.impact.tax_saved_vs_taxable_20yr || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>
          )}

          {/* Before / After comparison */}
          {result.current && result.projected && result.scenario_type !== 'tfsa_contribution' && (
            <div className="compare-grid">
              <CompareCard label="Taxable Income" current={result.current.income} projected={result.projected.income} isCurrency />
              <CompareCard label="Total Tax" current={result.current.tax_liability} projected={result.projected.tax_liability} isCurrency />
              <CompareCard label="Federal Tax" current={result.current.federal_tax} projected={result.projected.federal_tax} isCurrency />
              <CompareCard label="Provincial Tax" current={result.current.provincial_tax} projected={result.projected.provincial_tax} isCurrency />
              <CompareCard label="Effective Rate" current={result.current.effective_rate} projected={result.projected.effective_rate} isPercent />
              <CompareCard label="Marginal Rate" current={result.current.marginal_rate} projected={result.projected.marginal_rate} isPercent />
              {result.current?.rrsp_room !== undefined && (
                <>
                  <CompareCard label="RRSP Room" current={result.current.rrsp_room} projected={result.projected.rrsp_room} isCurrency invertColor />
                  <CompareCard label="RRSP Max Tax Savings" current={result.current.rrsp_max_savings} projected={result.projected.rrsp_max_savings} isCurrency invertColor />
                  <CompareCard label="FHSA Tax Savings" current={result.current.fhsa_max_savings} projected={result.projected.fhsa_max_savings} isCurrency invertColor />
                  <CompareCard label="GST/HST Credit" current={result.current.gst_hst_credit} projected={result.projected.gst_hst_credit} isCurrency invertColor />
                  {(result.current.cwb > 0 || result.projected.cwb > 0) && (
                    <CompareCard label="Canada Workers Benefit" current={result.current.cwb} projected={result.projected.cwb} isCurrency invertColor />
                  )}
                </>
              )}
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

      {/* Multi-Year Planning */}
      <div className="card" style={{ marginTop: 'var(--space-6)', padding: 'var(--space-6)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
          <Calendar size={18} style={{ color: 'var(--ws-blue)' }} />
          <h3 style={{ margin: 0 }}>Multi-Year Planning</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
          <div>
            <label style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--font-semibold)', display: 'block', marginBottom: 'var(--space-1)' }}>Annual RRSP</label>
            <input type="number" className="simulator-input" value={myRrsp} onChange={(e) => setMyRrsp(Number(e.target.value))} min={0} max={31560} step={500} />
          </div>
          <div>
            <label style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--font-semibold)', display: 'block', marginBottom: 'var(--space-1)' }}>Annual TFSA</label>
            <input type="number" className="simulator-input" value={myTfsa} onChange={(e) => setMyTfsa(Number(e.target.value))} min={0} max={7000} step={500} />
          </div>
          <div>
            <label style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--font-semibold)', display: 'block', marginBottom: 'var(--space-1)' }}>Annual FHSA</label>
            <input type="number" className="simulator-input" value={myFhsa} onChange={(e) => setMyFhsa(Number(e.target.value))} min={0} max={8000} step={500} />
          </div>
          <div>
            <label style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--font-semibold)', display: 'block', marginBottom: 'var(--space-1)' }}>Years</label>
            <input type="number" className="simulator-input" value={myYears} onChange={(e) => setMyYears(Number(e.target.value))} min={1} max={30} step={1} />
          </div>
        </div>
        <button onClick={handleMultiYear} disabled={multiYearRunning} className="btn btn-primary">
          {multiYearRunning ? <><LoadingSpinner size={14} /> Projecting...</> : <><Calendar size={16} /> Project Growth</>}
        </button>

        {multiYear && (
          <div className="animate-fade-in-up" style={{ marginTop: 'var(--space-5)' }}>
            <div className="summary-grid" style={{ marginBottom: 'var(--space-4)' }}>
              <div className="summary-card">
                <div className="summary-card-label">Total RRSP Tax Savings</div>
                <div className="summary-card-value text-green">
                  ${Number(multiYear.summary.total_rrsp_savings).toLocaleString('en-CA', { minimumFractionDigits: 0 })}
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-card-label">TFSA Balance</div>
                <div className="summary-card-value text-green">
                  ${Number(multiYear.summary.total_tfsa_balance).toLocaleString('en-CA', { minimumFractionDigits: 0 })}
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-card-label">TFSA Tax-Free Growth</div>
                <div className="summary-card-value text-green">
                  ${Number(multiYear.summary.total_tfsa_growth).toLocaleString('en-CA', { minimumFractionDigits: 0 })}
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-card-label">Total Benefit</div>
                <div className="summary-card-value text-green" style={{ fontWeight: 'var(--font-bold)' }}>
                  ${Number(multiYear.summary.total_benefit).toLocaleString('en-CA', { minimumFractionDigits: 0 })}
                </div>
              </div>
            </div>
            <div className="chart-card">
              <h4 style={{ margin: '0 0 var(--space-3)' }}>Cumulative Benefits Over {multiYear.years} Years</h4>
              <MultiYearChart data={multiYear} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
