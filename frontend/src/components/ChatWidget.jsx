import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { MessageCircle, X, Send, Loader2, Bot, User } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { usePageData } from '../context/PageDataContext'
import { sendChatMessage } from '../services/api'
import FormattedText from './FormattedText'
import '../styles/chat-widget.css'

function parseProfileId(search) {
  return new URLSearchParams(search).get('profile_id') || null
}

function parsePageContext(pathname) {
  const map = {
    '/': 'Home page',
    '/tax/documents': 'My Documents page',
    '/tax/analysis': 'Analysis page',
    '/tax/dashboard': 'Dashboard page',
    '/tax/insights': 'Insights page',
    '/tax/actions': 'Action Items page',
    '/tax/simulator': 'Simulator page',
    '/tax/ai-advisor': 'AI Advisor page',
    '/tax/trends': 'Trends page',
    '/tax/advisor': 'Advisor Dashboard',
    '/stocks': 'Stock Research page',
  }
  return map[pathname] || pathname
}

/** Build a concise summary of what's on the current page for the LLM */
function summarizePageData(pageData) {
  if (!pageData?.data) return ''
  const { page, data } = pageData
  const parts = []

  if (page === 'dashboard') {
    parts.push(`Current Page Data (Dashboard):`)
    if (data.income) parts.push(`  Income: $${Number(data.income).toLocaleString('en-CA')}`)
    if (data.tax_liability) parts.push(`  Tax Liability: $${Number(data.tax_liability).toLocaleString('en-CA')}`)
    if (data.total_savings) parts.push(`  Total Savings Found: $${Number(data.total_savings).toLocaleString('en-CA')}`)
    if (data.marginal_rate != null) parts.push(`  Marginal Rate: ${(data.marginal_rate * 100).toFixed(1)}%`)
    if (data.confidence != null) parts.push(`  Analysis Confidence: ${(data.confidence * 100).toFixed(0)}%`)
    if (data.tax_year) parts.push(`  Tax Year: ${data.tax_year}`)
    if (data.insights_by_category) {
      const cats = Object.entries(data.insights_by_category)
      for (const [cat, items] of cats) {
        if (items.length > 0) {
          parts.push(`  ${cat.replace('_', ' ')} insights (${items.length}):`)
          for (const item of items.slice(0, 3)) {
            parts.push(`    - ${item.headline || item.name || ''}${item.estimated_value ? ` ($${item.estimated_value})` : ''}`)
          }
        }
      }
    }
  } else if (page === 'insights') {
    const insights = data.insights || []
    const summary = data.summary || {}
    parts.push(`Current Page Data (Insights): ${insights.length} insights found`)
    if (summary.total_identified_savings) parts.push(`  Total Savings: $${Number(summary.total_identified_savings).toLocaleString('en-CA')}`)
    for (const ins of insights.slice(0, 5)) {
      parts.push(`  - [${ins.priority}] ${ins.headline}${ins.estimated_value ? ` ($${Number(ins.estimated_value).toLocaleString('en-CA')})` : ''}`)
      if (ins.detail) parts.push(`    ${ins.detail.slice(0, 150)}`)
    }
    if (insights.length > 5) parts.push(`  ... and ${insights.length - 5} more insights`)
  } else if (page === 'action_items') {
    const items = data.action_items || []
    const summary = data.summary || {}
    parts.push(`Current Page Data (Action Items): ${summary.pending || 0} pending, ${summary.completed || 0} completed`)
    if (summary.total_savings) parts.push(`  Potential Savings: $${Number(summary.total_savings).toLocaleString('en-CA')}`)
    for (const item of items.filter(i => i.status === 'pending').slice(0, 5)) {
      parts.push(`  - [${item.priority}] ${item.title}${item.deadline ? ` (due: ${item.deadline})` : ''}`)
    }
  } else if (page === 'trends') {
    parts.push(`Current Page Data (Trends):`)
    if (data.years) parts.push(`  Years: ${data.years.join(', ')}`)
    if (data.income) {
      data.years.forEach((y, i) => {
        parts.push(`  ${y}: Income $${Number(data.income[i]).toLocaleString('en-CA')}, Tax $${Number(data.tax_paid[i]).toLocaleString('en-CA')}, Eff. Rate ${(data.effective_rate[i] * 100).toFixed(1)}%, Savings $${Number(data.savings[i]).toLocaleString('en-CA')}`)
      })
    }
  } else if (page === 'ai_advisor') {
    parts.push(`Current Page Data (AI Advisor):`)
    if (data.health_score?.overall) parts.push(`  Financial Health Score: ${Math.round(data.health_score.overall)}/100`)
    if (data.health_score?.components) {
      const c = data.health_score.components
      if (c.rrsp_utilization != null) parts.push(`  RRSP Utilization: ${Math.round(c.rrsp_utilization)}%`)
      if (c.tfsa_utilization != null) parts.push(`  TFSA Utilization: ${Math.round(c.tfsa_utilization)}%`)
      if (c.tax_efficiency != null) parts.push(`  Tax Efficiency: ${Math.round(c.tax_efficiency)}%`)
    }
    if (data.last_year) {
      const ly = data.last_year
      parts.push(`  Last Year (${ly.tax_year}): Income $${Number(ly.income).toLocaleString('en-CA')}, Tax $${Number(ly.tax_paid).toLocaleString('en-CA')}`)
      if (ly.rrsp_room_remaining) parts.push(`  RRSP Room: $${Number(ly.rrsp_room_remaining).toLocaleString('en-CA')}`)
      if (ly.tfsa_room_remaining) parts.push(`  TFSA Room: $${Number(ly.tfsa_room_remaining).toLocaleString('en-CA')}`)
    }
    if (data.recommendations) {
      parts.push(`  Recommendations (${data.recommendations.length}):`)
      for (const rec of data.recommendations.slice(0, 5)) {
        parts.push(`    - [${rec.priority}] ${rec.this_year}${rec.estimated_value ? ` ($${Number(rec.estimated_value).toLocaleString('en-CA')})` : ''}`)
      }
    }
  } else if (page === 'simulator') {
    parts.push(`Current Page Data (Simulator):`)
    if (data.scenario) parts.push(`  Scenario: ${data.scenario}`)
    if (data.result?.impact?.tax_savings) parts.push(`  Tax Savings: $${Number(data.result.impact.tax_savings).toLocaleString('en-CA')}`)
    if (data.result?.current && data.result?.projected) {
      parts.push(`  Current Tax: $${Number(data.result.current.tax_liability).toLocaleString('en-CA')}`)
      parts.push(`  Projected Tax: $${Number(data.result.projected.tax_liability).toLocaleString('en-CA')}`)
    }
    if (data.result?.explanation) parts.push(`  Explanation: ${data.result.explanation.slice(0, 300)}`)
  }

  return parts.join('\n')
}

export default function ChatWidget() {
  const { isAuthenticated, user } = useAuth()
  const { pageData } = usePageData()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const profileId = parseProfileId(location.search)
  const pageContext = parsePageContext(location.pathname)
  const pageDataSummary = useMemo(() => summarizePageData(pageData), [pageData])

  const handleSend = useCallback(async () => {
    const question = input.trim()
    if (!question || streaming) return

    const userMsg = { role: 'user', content: question }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    setInput('')
    setStreaming(true)

    // Add placeholder for assistant response
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      const stream = await sendChatMessage({
        question,
        profileId,
        pageContext,
        pageDataSummary,
        userId: user?.id,
        history: updatedMessages.slice(-10),
      })

      const reader = stream.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.content) {
                setMessages(prev => {
                  const updated = [...prev]
                  const last = updated.length - 1
                  updated[last] = { ...updated[last], content: updated[last].content + data.content }
                  return updated
                })
              }
            } catch {
              // skip malformed
            }
          }
        }
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        const last = updated.length - 1
        if (updated[last].role === 'assistant' && !updated[last].content) {
          updated[last] = { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' }
        }
        return updated
      })
    } finally {
      setStreaming(false)
    }
  }, [input, streaming, messages, profileId, pageContext, pageDataSummary, user])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!isAuthenticated) return null

  return (
    <>
      {!open && (
        <button className="chat-fab" onClick={() => setOpen(true)} title="Tax Copilot">
          <MessageCircle size={24} />
        </button>
      )}

      {open && (
        <div className="chat-panel animate-fade-in">
          <div className="chat-header">
            <div className="chat-header-left">
              <Bot size={18} />
              <span>Tax Copilot</span>
            </div>
            <button className="chat-close" onClick={() => setOpen(false)}>
              <X size={18} />
            </button>
          </div>

          <div className="chat-messages">
            {messages.length === 0 && (
              <div className="chat-welcome">
                <Bot size={32} style={{ color: 'var(--ws-grey-300)', marginBottom: 'var(--space-2)' }} />
                <p style={{ fontWeight: 'var(--font-semibold)', color: 'var(--ws-grey-700)' }}>
                  Hi! I'm your Tax Copilot.
                </p>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--ws-grey-500)' }}>
                  Ask me about your tax data, insights, or Canadian tax rules.
                </p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
                <div className="chat-msg-icon">
                  {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                </div>
                <div className="chat-msg-content">
                  {msg.content ? (
                    msg.role === 'assistant' ? <FormattedText text={msg.content} /> : msg.content
                  ) : (streaming && i === messages.length - 1 ? (
                    <span className="chat-typing">
                      <span></span><span></span><span></span>
                    </span>
                  ) : null)}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-bar">
            <input
              ref={inputRef}
              className="chat-input"
              placeholder="Ask about your taxes..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={streaming}
            />
            <button
              className="chat-send"
              onClick={handleSend}
              disabled={!input.trim() || streaming}
            >
              {streaming ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>
      )}
    </>
  )
}
