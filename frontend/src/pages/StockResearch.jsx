import { useState, useEffect, useCallback, useRef } from 'react'
import { Search, TrendingUp, TrendingDown, Minus, Clock, ArrowRight, AlertTriangle, RotateCcw, History, Info } from 'lucide-react'
import { searchStocks, getResearchHistory, getAuthToken } from '../services/api'
import StockPipelineProgress from '../components/StockPipelineProgress'
import StockNewsInsights from '../components/StockNewsInsights'
import { LoadingSpinner } from '../components/LoadingState'
import '../styles/dashboard.css'

export default function StockResearch() {
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)

  const [step, setStep] = useState('idle') // idle, streaming, done, error
  const [stages, setStages] = useState({})
  const [complete, setComplete] = useState(null)

  // Agent data as it streams in
  const [marketData, setMarketData] = useState(null)
  const [indicators, setIndicators] = useState(null)
  const [sentiment, setSentiment] = useState(null)
  const [geoPolicy, setGeoPolicy] = useState(null)
  const [volatility, setVolatility] = useState(null)
  const [signalResult, setSignalResult] = useState(null)

  const [history, setHistory] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(true)

  const searchTimeout = useRef(null)
  const dropdownRef = useRef(null)

  // Load research history on mount
  useEffect(() => {
    getResearchHistory(10)
      .then(res => setHistory(res.history || []))
      .catch(() => {})
      .finally(() => setLoadingHistory(false))
  }, [])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Debounced search
  const handleSearchInput = (value) => {
    setQuery(value)
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    if (value.trim().length < 1) {
      setSearchResults([])
      setShowDropdown(false)
      return
    }
    setSearching(true)
    searchTimeout.current = setTimeout(() => {
      searchStocks(value.trim())
        .then(res => {
          setSearchResults(res.results || [])
          setShowDropdown(true)
        })
        .catch(() => setSearchResults([]))
        .finally(() => setSearching(false))
    }, 400)
  }

  const resetState = () => {
    setStages({})
    setComplete(null)
    setMarketData(null)
    setIndicators(null)
    setSentiment(null)
    setGeoPolicy(null)
    setVolatility(null)
    setSignalResult(null)
  }

  const runResearch = useCallback((ticker) => {
    setQuery(ticker)
    setShowDropdown(false)
    setStep('streaming')
    resetState()

    const token = getAuthToken()
    const eventSource = new EventSource(`/api/stocks/research/${ticker}/stream?token=${token}`)

    eventSource.addEventListener('stage', (e) => {
      const data = JSON.parse(e.data)
      setStages(prev => ({
        ...prev,
        [data.stage]: data.status,
        [`${data.stage}_message`]: data.message,
        [`${data.stage}_agent_name`]: data.agent_name,
      }))
    })

    eventSource.addEventListener('market_data', (e) => {
      setMarketData(JSON.parse(e.data))
    })

    eventSource.addEventListener('indicators', (e) => {
      setIndicators(JSON.parse(e.data))
    })

    eventSource.addEventListener('sentiment', (e) => {
      setSentiment(JSON.parse(e.data))
    })

    eventSource.addEventListener('geo_policy', (e) => {
      setGeoPolicy(JSON.parse(e.data))
    })

    eventSource.addEventListener('volatility', (e) => {
      setVolatility(JSON.parse(e.data))
    })

    eventSource.addEventListener('signal', (e) => {
      setSignalResult(JSON.parse(e.data))
    })

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data)
      setComplete(data)
      setStep('done')
      eventSource.close()
      // Refresh history
      getResearchHistory(10)
        .then(res => setHistory(res.history || []))
        .catch(() => {})
    })

    eventSource.addEventListener('error', (e) => {
      try {
        const data = JSON.parse(e.data)
        console.error('Research error:', data.message)
      } catch {}
      setStep('error')
      eventSource.close()
    })

    eventSource.onerror = () => {
      setStep('error')
      eventSource.close()
    }
  }, [])

  const outlookColor = (signal) => {
    if (signal === 'BULLISH') return 'var(--ws-green)'
    if (signal === 'BEARISH') return '#ef4444'
    return 'var(--ws-amber)'
  }

  const outlookIcon = (signal) => {
    if (signal === 'BULLISH') return <TrendingUp size={16} />
    if (signal === 'BEARISH') return <TrendingDown size={16} />
    return <Minus size={16} />
  }

  return (
    <div className="page-container" style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">Stock Research</h1>
          <p className="page-subtitle">AI-powered multi-agent market insights</p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="stock-disclaimer">
        <Info size={16} className="stock-disclaimer-icon" />
        <p>
          <strong>For informational purposes only.</strong> The insights provided here are AI-generated observations based on publicly available market data, news, and technical indicators. They do not constitute financial advice, investment recommendations, or solicitations to buy or sell any securities. Always conduct your own research and consult a qualified financial advisor before making investment decisions.
        </p>
      </div>

      {/* Search Bar */}
      <div className="stock-search-wrap" ref={dropdownRef}>
        <div className="stock-search-input-wrap">
          <Search size={18} className="stock-search-icon" />
          <input
            type="text"
            className="stock-search-input"
            placeholder="Search by ticker or company name (e.g. AAPL, Tesla)"
            value={query}
            onChange={(e) => handleSearchInput(e.target.value)}
            onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && query.trim()) {
                runResearch(query.trim().toUpperCase())
              }
            }}
          />
          {searching && <LoadingSpinner size={16} />}
        </div>
        {showDropdown && searchResults.length > 0 && (
          <div className="stock-search-dropdown">
            {searchResults.map((r, i) => (
              <button
                key={i}
                className="stock-search-result"
                onClick={() => runResearch(r.symbol)}
              >
                <span className="stock-result-symbol">{r.symbol}</span>
                <span className="stock-result-name">{r.name}</span>
                {r.exchange && <span className="stock-result-exchange">{r.exchange}</span>}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Pipeline Progress */}
      {(step === 'streaming' || step === 'done') && (
        <StockPipelineProgress stages={stages} complete={complete} />
      )}

      {/* Error State */}
      {step === 'error' && (
        <div className="animate-fade-in" style={{ textAlign: 'center', marginTop: 'var(--space-6)' }}>
          <div className="error-banner" style={{ justifyContent: 'center', marginBottom: 'var(--space-4)' }}>
            <AlertTriangle size={18} className="banner-icon" />
            Research failed. Check the ticker symbol and try again.
          </div>
          <button onClick={() => setStep('idle')} className="btn btn-secondary">
            <RotateCcw size={16} />
            Retry
          </button>
        </div>
      )}

      {/* Results - shown when done */}
      {step === 'done' && signalResult && (
        <div className="stock-results animate-fade-in-up">
          {/* Market Outlook Card */}
          <div className="card stock-signal-card">
            <div className="stock-outlook-label">Market Outlook</div>
            <div className="stock-signal-header">
              <div className="stock-signal-main" style={{ color: outlookColor(signalResult.signal) }}>
                {outlookIcon(signalResult.signal)}
                <span className="stock-signal-text">{signalResult.signal}</span>
              </div>
              <div className="stock-confidence-gauge">
                <div className="stock-confidence-bar">
                  <div className="stock-confidence-fill" style={{ width: `${(signalResult.confidence || 0) * 100}%`, backgroundColor: outlookColor(signalResult.signal) }} />
                </div>
                <span className="stock-confidence-label">{((signalResult.confidence || 0) * 100).toFixed(0)}% confidence</span>
              </div>
            </div>
            {signalResult.reasoning && (
              <p className="stock-reasoning">{signalResult.reasoning}</p>
            )}
            {signalResult.risk_warning && (
              <p className="stock-risk-warning">{signalResult.risk_warning}</p>
            )}
          </div>

          {/* Technical Indicators */}
          {indicators && !indicators.error && (
            <div className="card">
              <h3 className="card-heading">Technical Indicators</h3>
              <div className="stock-indicators-grid">
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">RSI (14)</div>
                  <div className={`stock-indicator-value ${indicators.rsi_14 > 70 ? 'text-red' : indicators.rsi_14 < 30 ? 'text-green' : ''}`}>
                    {indicators.rsi_14}
                  </div>
                  <div className="stock-indicator-desc">
                    {indicators.rsi_14 > 70 ? 'Overbought' : indicators.rsi_14 < 30 ? 'Oversold' : 'Neutral'}
                  </div>
                </div>
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">MACD</div>
                  <div className={`stock-indicator-value ${(indicators.macd?.histogram || 0) > 0 ? 'text-green' : 'text-red'}`}>
                    {indicators.macd?.histogram?.toFixed(2) || 'N/A'}
                  </div>
                  <div className="stock-indicator-desc">
                    {(indicators.macd?.histogram || 0) > 0 ? 'Bullish' : 'Bearish'}
                  </div>
                </div>
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">SMA Crossover</div>
                  <div className={`stock-indicator-value ${indicators.sma_crossover === 'golden_cross' ? 'text-green' : indicators.sma_crossover === 'death_cross' ? 'text-red' : ''}`}>
                    {indicators.sma_crossover === 'golden_cross' ? 'Golden Cross' : indicators.sma_crossover === 'death_cross' ? 'Death Cross' : 'Neutral'}
                  </div>
                </div>
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">Bollinger</div>
                  <div className="stock-indicator-value">
                    {indicators.bollinger_bands?.position === 'upper' ? 'Upper Band' : indicators.bollinger_bands?.position === 'lower' ? 'Lower Band' : 'Middle'}
                  </div>
                </div>
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">Trend</div>
                  <div className={`stock-indicator-value ${indicators.trend_summary === 'bullish' ? 'text-green' : indicators.trend_summary === 'bearish' ? 'text-red' : ''}`}>
                    {indicators.trend_summary?.charAt(0).toUpperCase() + indicators.trend_summary?.slice(1)}
                  </div>
                </div>
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">SMA 20</div>
                  <div className="stock-indicator-value">${indicators.sma_20?.toFixed(2) || 'N/A'}</div>
                </div>
              </div>
            </div>
          )}

          {/* Sentiment */}
          {sentiment && (
            <div className="card">
              <h3 className="card-heading">News Sentiment</h3>
              <div className="stock-sentiment-bar-wrap">
                <span className="stock-sentiment-label-left">Bearish</span>
                <div className="stock-sentiment-track">
                  <div
                    className="stock-sentiment-marker"
                    style={{ left: `${((sentiment.sentiment_score || 0) + 1) / 2 * 100}%` }}
                  />
                </div>
                <span className="stock-sentiment-label-right">Bullish</span>
              </div>
              <div className="stock-sentiment-score">
                Score: {(sentiment.sentiment_score || 0).toFixed(2)} — {sentiment.overall_sentiment?.replace(/_/g, ' ')}
              </div>
              {sentiment.key_themes?.length > 0 && (
                <div className="stock-themes">
                  {sentiment.key_themes.map((theme, i) => (
                    <span key={i} className="stock-theme-tag">{theme}</span>
                  ))}
                </div>
              )}
              {sentiment.summary && <p className="text-muted" style={{ marginTop: 'var(--space-2)' }}>{sentiment.summary}</p>}
            </div>
          )}

          {/* Geo-Policy */}
          {geoPolicy && (
            <div className="card">
              <h3 className="card-heading">Geo-Policy Impact</h3>
              <div className="stock-geo-impact" style={{ color: geoPolicy.policy_impact === 'positive' ? 'var(--ws-green)' : geoPolicy.policy_impact === 'negative' ? '#ef4444' : 'var(--ws-amber)' }}>
                Impact: {geoPolicy.policy_impact} ({(geoPolicy.impact_score || 0).toFixed(2)})
              </div>
              {geoPolicy.risk_factors?.length > 0 && (
                <div className="stock-risk-factors">
                  {geoPolicy.risk_factors.map((rf, i) => (
                    <div key={i} className="stock-risk-factor">
                      <span className={`stock-rf-severity stock-rf-${(rf.severity || 'low').toLowerCase()}`}>
                        {rf.severity || 'LOW'}
                      </span>
                      <span>{rf.factor}</span>
                    </div>
                  ))}
                </div>
              )}
              {geoPolicy.summary && <p className="text-muted" style={{ marginTop: 'var(--space-2)' }}>{geoPolicy.summary}</p>}
            </div>
          )}

          {/* Volatility & Risk */}
          {volatility && !volatility.error && (
            <div className="card">
              <h3 className="card-heading">Volatility & Risk</h3>
              <div className="stock-indicators-grid">
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">Risk Level</div>
                  <div className={`stock-indicator-value ${volatility.risk_level === 'HIGH' ? 'text-red' : volatility.risk_level === 'MODERATE' ? 'text-amber' : 'text-green'}`}>
                    {volatility.risk_level}
                  </div>
                </div>
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">Volatility</div>
                  <div className="stock-indicator-value">{(volatility.annualized_volatility * 100).toFixed(1)}%</div>
                  <div className="stock-indicator-desc">{volatility.volatility_regime}</div>
                </div>
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">Max Drawdown</div>
                  <div className="stock-indicator-value text-red">{(volatility.max_drawdown * 100).toFixed(1)}%</div>
                </div>
                <div className="stock-indicator-card">
                  <div className="stock-indicator-label">Sharpe Ratio</div>
                  <div className={`stock-indicator-value ${volatility.sharpe_ratio > 0 ? 'text-green' : 'text-red'}`}>
                    {volatility.sharpe_ratio?.toFixed(2)}
                  </div>
                </div>
              </div>
              {volatility.risk_factors?.length > 0 && (
                <div className="stock-vol-factors">
                  {volatility.risk_factors.map((f, i) => (
                    <div key={i} className="stock-vol-factor">{f}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Bull/Bear Cases */}
          {signalResult && (signalResult.bull_case || signalResult.bear_case) && (
            <div className="card">
              <h3 className="card-heading">Analysis</h3>
              <div className="stock-cases-grid">
                {signalResult.bull_case && (
                  <div className="stock-case stock-case-bull">
                    <div className="stock-case-header">
                      <TrendingUp size={16} /> Bull Case
                    </div>
                    <p>{signalResult.bull_case}</p>
                  </div>
                )}
                {signalResult.bear_case && (
                  <div className="stock-case stock-case-bear">
                    <div className="stock-case-header">
                      <TrendingDown size={16} /> Bear Case
                    </div>
                    <p>{signalResult.bear_case}</p>
                  </div>
                )}
              </div>
              {signalResult.key_factors?.length > 0 && (
                <div className="stock-key-factors">
                  <h4 className="stock-kf-title">Key Factors</h4>
                  {signalResult.key_factors.map((kf, i) => (
                    <div key={i} className="stock-key-factor">
                      <span className={`stock-kf-impact stock-kf-${kf.impact || 'neutral'}`}>
                        {kf.impact === 'positive' ? '+' : kf.impact === 'negative' ? '-' : '~'}
                      </span>
                      <span>{kf.factor}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* News & Insights — shown after research completes */}
      {step === 'done' && complete && (
        <StockNewsInsights
          ticker={complete.ticker}
          companyName={complete.company_name}
        />
      )}

      {/* Research History */}
      {step === 'idle' && (
        <div className="stock-history-section">
          <h3 className="card-heading" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <History size={18} /> Recent Research
          </h3>
          {loadingHistory ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)' }}><LoadingSpinner size={20} /></div>
          ) : history.length === 0 ? (
            <p className="text-muted" style={{ textAlign: 'center', padding: 'var(--space-6)' }}>
              No research history yet. Search for a stock to get started.
            </p>
          ) : (
            <div className="stock-history-list">
              {history.map(r => (
                <button
                  key={r.id}
                  className="stock-history-item"
                  onClick={() => runResearch(r.ticker)}
                >
                  <div className="stock-history-info">
                    <span className="stock-history-ticker">{r.ticker}</span>
                    <span className="stock-history-name">{r.company_name}</span>
                  </div>
                  <div className="stock-history-meta">
                    <span
                      className="stock-history-signal"
                      style={{ color: outlookColor(r.signal) }}
                    >
                      {outlookIcon(r.signal)} {r.signal || 'NEUTRAL'}
                    </span>
                    <span className="stock-history-price">${r.price_at_research?.toFixed(2)}</span>
                    <span className="stock-history-date">
                      <Clock size={12} /> {new Date(r.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <ArrowRight size={16} className="stock-history-arrow" />
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
