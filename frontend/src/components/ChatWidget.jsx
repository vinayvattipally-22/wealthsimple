import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, Loader2, Bot, User } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { sendChatMessage } from '../services/api'
import FormattedText from './FormattedText'
import '../styles/chat-widget.css'

function parseProfileId(search) {
  return new URLSearchParams(search).get('profile_id') || null
}

function parsePageContext(pathname) {
  const map = {
    '/': 'My Documents page',
    '/upload': 'Upload page',
    '/analysis': 'Analysis page',
    '/dashboard': 'Dashboard page',
    '/insights': 'Insights page',
    '/trends': 'Trends page',
    '/advisor': 'Advisor Dashboard',
  }
  return map[pathname] || pathname
}

export default function ChatWidget() {
  const { isAuthenticated } = useAuth()
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
  }, [input, streaming, messages, profileId, pageContext])

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
