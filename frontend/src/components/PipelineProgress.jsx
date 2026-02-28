import { CheckCircle2, Loader2, FileSearch, Calculator, Brain, BookOpen, Lightbulb, ShieldCheck, ListChecks } from 'lucide-react'
import '../styles/dashboard.css'

const AGENTS = [
  { key: 'extraction', icon: FileSearch, name: 'Data Extractor', desc: 'Loading and validating profile data' },
  { key: 'tax_engine', icon: Calculator, name: 'Tax Calculator', desc: 'Computing tax liability and rates' },
  { key: 'llm_analysis', icon: Brain, name: 'Tax Strategist', desc: 'Finding optimization opportunities with AI' },
  { key: 'rag_query', icon: BookOpen, name: 'Knowledge Researcher', desc: 'Querying CRA tax knowledge base' },
  { key: 'benefit_engine', icon: Lightbulb, name: 'Insight Generator', desc: 'Building prioritized insights' },
  { key: 'compliance', icon: ShieldCheck, name: 'Compliance Checker', desc: 'Checking audit risk and deadlines' },
  { key: 'action_planner', icon: ListChecks, name: 'Action Planner', desc: 'Creating your action plan' },
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

export default function PipelineProgress({ stages, insights, complianceFlags, complete }) {
  const doneCount = AGENTS.filter(a => stages[a.key] === 'complete').length
  const progress = (doneCount / AGENTS.length) * 100
  const isAnalyzing = !complete

  return (
    <div className="pipeline-progress">
      {/* Progress bar */}
      {isAnalyzing && (
        <div className="analyzing-progress-bar" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="analyzing-progress-fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      {/* Agent cards */}
      <div className="agent-grid">
        {AGENTS.map((agent) => (
          <AgentCard key={agent.key} agent={agent} stages={stages} />
        ))}
      </div>

      {/* Compliance flags */}
      {complianceFlags && complianceFlags.length > 0 && (
        <div className="compliance-flags" style={{ marginTop: 'var(--space-4)' }}>
          {complianceFlags.map((flag, i) => (
            <div
              key={i}
              className={`compliance-flag compliance-flag-${flag.severity || 'info'}`}
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <ShieldCheck size={14} />
              <span>{flag.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Insights arriving in real-time */}
      {insights.length > 0 && !complete && (
        <div className="pipeline-insights-list">
          <div className="heading-3" style={{ marginTop: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Lightbulb size={18} />
            Findings
          </div>
          {insights.map((ins, i) => (
            <div
              key={i}
              className="pipeline-insight-item"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <span className="insight-name">{ins.headline}</span>
              {ins.estimated_value != null && (
                <span className="insight-val">
                  +${Number(ins.estimated_value).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Completion banner */}
      {complete && (
        <div className="pipeline-complete-banner">
          <CheckCircle2 size={32} className="complete-icon" />
          <div className="complete-title">Analysis Complete</div>
          <div className="complete-detail">
            {complete.total_insights} insights found &middot; ${Number(complete.total_savings || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })} in potential savings
            {complete.action_items_count > 0 && (
              <> &middot; {complete.action_items_count} action items created</>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
