import { CheckCircle2, Loader2, Database, LineChart, Newspaper, Globe, Activity, Zap } from 'lucide-react'
import '../styles/dashboard.css'

const AGENTS = [
  { key: 'market_data', icon: Database, name: 'Market Data Agent', desc: 'Fetching stock price, company info, and financials' },
  { key: 'technical', icon: LineChart, name: 'Technical Analyst', desc: 'Computing SMA, RSI, MACD, Bollinger Bands' },
  { key: 'sentiment', icon: Newspaper, name: 'Sentiment Analyst', desc: 'Analyzing recent news for market sentiment' },
  { key: 'geo_policy', icon: Globe, name: 'Geo-Policy Analyst', desc: 'Assessing political and regulatory impact' },
  { key: 'volatility', icon: Activity, name: 'Risk Analyst', desc: 'Computing volatility metrics and risk assessment' },
  { key: 'signal', icon: Zap, name: 'Outlook Aggregator', desc: 'Combining all analyses into a market outlook' },
]

function AgentCard({ agent, stages }) {
  const status = stages[agent.key]
  const message = stages[`${agent.key}_message`]
  const agentName = stages[`${agent.key}_agent_name`] || agent.name
  const Icon = agent.icon

  const isRunning = status === 'running'
  const isComplete = status === 'complete'
  const isWaiting = !status

  return (
    <div className={`agent-card ${isRunning ? 'agent-card-active' : ''} ${isComplete ? 'agent-card-complete' : ''}`}>
      <div className="agent-card-icon">
        {isRunning ? (
          <Loader2 size={20} className="animate-spin" style={{ color: 'var(--ws-blue)' }} />
        ) : isComplete ? (
          <CheckCircle2 size={20} style={{ color: 'var(--ws-green)' }} />
        ) : (
          <Icon size={20} style={{ color: 'var(--ws-grey-400)' }} />
        )}
      </div>
      <div className="agent-card-content">
        <div className="agent-card-name">{agentName}</div>
        {isRunning && message && (
          <div className="agent-card-message">{message}</div>
        )}
        {isComplete && message && (
          <div className="agent-card-message agent-card-message-done">{message}</div>
        )}
        {isWaiting && (
          <div className="agent-card-message agent-card-message-waiting">{agent.desc}</div>
        )}
      </div>
    </div>
  )
}

function OutlookBadge({ signal, confidence }) {
  const colorMap = { BULLISH: 'var(--ws-green)', NEUTRAL: 'var(--ws-amber)', BEARISH: '#ef4444' }
  const color = colorMap[signal] || 'var(--ws-grey-400)'

  return (
    <div className="stock-signal-badge" style={{ borderColor: color }}>
      <span className="stock-signal-label" style={{ color }}>{signal}</span>
      {confidence != null && (
        <span className="stock-signal-confidence">{(confidence * 100).toFixed(0)}% confidence</span>
      )}
    </div>
  )
}

export default function StockPipelineProgress({ stages, complete }) {
  const doneCount = AGENTS.filter(a => stages[a.key] === 'complete').length
  const progress = (doneCount / AGENTS.length) * 100
  const isAnalyzing = !complete

  return (
    <div className="pipeline-progress">
      {isAnalyzing && (
        <div className="analyzing-progress-bar" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="analyzing-progress-fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      <div className="agent-grid">
        {AGENTS.map((agent) => (
          <AgentCard key={agent.key} agent={agent} stages={stages} />
        ))}
      </div>

      {complete && (
        <div className="pipeline-complete-banner">
          <OutlookBadge signal={complete.signal} confidence={complete.confidence} />
          <div className="complete-title">Insights Ready</div>
          <div className="complete-detail">
            {complete.company_name} ({complete.ticker}) &middot; ${Number(complete.current_price || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>
      )}
    </div>
  )
}
