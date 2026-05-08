import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { Send, Trash2, Plus } from 'lucide-react'
import { queryLegal } from '../api/client'
import { useWorkspace } from '../context/WorkspaceContext'
import { RiskBadge, ConfidenceBadge } from '../components/ScoreBadge'
import GuidancePanel    from '../components/GuidancePanel'
import GuardrailBanner  from '../components/GuardrailBanner'
import LoadingSpinner   from '../components/LoadingSpinner'

function IntentTag({ intent }) {
  if (!intent) return null
  return (
    <span className="tag tag-info" style={{ fontSize: 11 }}>
      {intent.replace(/_/g, ' ')}
    </span>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 20
    }}>
      <div style={{
        maxWidth: '78%', display: 'flex',
        flexDirection: 'column', gap: 8,
        alignItems: isUser ? 'flex-end' : 'flex-start'
      }}>
        <div style={{
          background: isUser ? 'var(--accent)' : 'var(--surface)',
          border: isUser ? 'none' : '1px solid var(--border)',
          borderRadius: isUser ? '18px 18px 4px 18px' : '4px 18px 18px 18px',
          padding: '12px 16px',
          color: isUser ? '#fff' : 'var(--text)',
          fontSize: 14, lineHeight: 1.65
        }}>
          {isUser
            ? <span>{msg.content}</span>
            : <div className="prose">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
          }
        </div>

        {!isUser && msg.intent    && <IntentTag intent={msg.intent} />}
        {!isUser && msg.guardrails && (
          <div style={{ width: '100%' }}>
            <GuardrailBanner guardrails={msg.guardrails} />
          </div>
        )}
        {!isUser && msg.scores && (
          <div style={{ display: 'flex', flexDirection: 'column',
            gap: 8, width: '100%' }}>
            <RiskBadge
              score={msg.scores.risk?.score || 0}
              display={msg.scores.risk?.display}
            />
            <ConfidenceBadge
              score={msg.scores.confidence?.score || 0}
              display={msg.scores.confidence?.display}
            />
          </div>
        )}
        {!isUser && msg.guidance && (
          <div className="card" style={{ width: '100%' }}>
            <div className="section-title" style={{ marginBottom: 14 }}>
              Legal Guidance
            </div>
            <GuidancePanel guidance={msg.guidance} />
          </div>
        )}
      </div>
    </div>
  )
}

export default function Chat() {
  const { activeWs, activeSession, setActiveSession } = useWorkspace()

  const [messages,  setMessages]  = useState([])
  const [input,     setInput]     = useState('')
  const [loading,   setLoading]   = useState(false)
  const [sessLoading, setSessLoading] = useState(false)
  const bottomRef                 = useRef(null)
  const inputRef                  = useRef(null)

  const wsId   = activeWs?.id   || null
  const sessId = activeSession   || null

  // Load history when session changes
  useEffect(() => {
    if (!sessId || !wsId) {
      setMessages([])
      return
    }
    setSessLoading(true)
    getChatHistory(wsId, sessId)
      .then(r => {
        const hist = r.data.messages || []
        setMessages(hist.map(m => ({ role: m.role, content: m.content })))
      })
      .catch(() => setMessages([]))
      .finally(() => setSessLoading(false))
  }, [sessId, wsId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function ensureSession() {
    if (sessId) return sessId
    if (!wsId)  return null
    const { data } = await createChatSession(wsId, input.slice(0, 60) || 'New Chat')
    setActiveSession(data.session_id)
    return data.session_id
  }

  async function send() {
    const q = input.trim()
    if (!q || loading) return

    setMessages(prev => [...prev, { role: 'user', content: q }])
    setInput('')
    setLoading(true)

    const chatHistory = messages.map(m => ({
      role: m.role, content: m.content
    }))

    try {
      const currentSessId = await ensureSession()
      const { data }      = await queryLegal(q, chatHistory, wsId, currentSessId)

      setMessages(prev => [...prev, {
        role:       'assistant',
        content:    data.answer,
        intent:     data.intent,
        guardrails: data.guardrails,
        scores:     data.scores,
        guidance:   data.guidance
      }])
    } catch {
      setMessages(prev => [...prev, {
        role:    'assistant',
        content: '⚠️ Request failed. Please check the server is running.'
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function newChat() {
    setActiveSession(null)
    setMessages([])
    setInput('')
  }

  const headerTitle = activeWs
    ? `Legal Chat — ${activeWs.name}`
    : 'Legal Chat'

  const headerSub = sessId
    ? 'Continuing saved session'
    : wsId
    ? 'New session in workspace'
    : 'Global session (not saved)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* Header */}
      <div style={{
        padding: '14px 22px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', gap: 10, flexWrap: 'wrap'
      }}>
        <div>
          <h1 style={{ fontSize: 16, fontWeight: 700 }}>{headerTitle}</h1>
          <p style={{ fontSize: 11, color: 'var(--muted)' }}>{headerSub}</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {wsId && (
            <button className="btn btn-secondary"
              style={{ padding: '7px 12px', fontSize: 12 }}
              onClick={newChat}>
              <Plus size={13} /> New Chat
            </button>
          )}
          {messages.length > 0 && !sessId && (
            <button className="btn btn-secondary"
              style={{ padding: '7px 12px', fontSize: 12 }}
              onClick={() => setMessages([])}>
              <Trash2 size={13} /> Clear
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: '22px' }}>
        {sessLoading && <LoadingSpinner label="Loading session..." />}

        {!sessLoading && messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '50px 20px',
            color: 'var(--muted)' }}>
            <div style={{ fontSize: 38, marginBottom: 14 }}>⚖️</div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>
              Ask a Legal Question
            </div>
            <div style={{ fontSize: 13, maxWidth: 360, margin: '0 auto 20px' }}>
              {wsId
                ? 'Questions are searched against both the global legal corpus and your uploaded workspace documents.'
                : 'Questions are searched against the global legal corpus.'
              }
            </div>
            <div style={{
              display: 'flex', gap: 8, flexWrap: 'wrap',
              justifyContent: 'center'
            }}>
              {[
                'My landlord locked me out without notice',
                'How do I file an FIR?',
                'What is a penalty clause in a contract?',
                'Can my employer enforce a non-compete?'
              ].map(q => (
                <button
                  key={q}
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: '7px 14px' }}
                  onClick={() => { setInput(q); inputRef.current?.focus() }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {!sessLoading && messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}

        {loading && <LoadingSpinner label="Analysing your query..." />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '14px 22px',
        borderTop: '1px solid var(--border)',
        background: 'var(--surface)',
        display: 'flex', gap: 10
      }}>
        <input
          ref={inputRef}
          className="input"
          placeholder={
            wsId
              ? 'Ask a legal question (searches workspace + global corpus)...'
              : 'Ask a legal question...'
          }
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          disabled={loading}
          style={{ flex: 1 }}
        />
        <button
          className="btn btn-primary"
          onClick={send}
          disabled={loading || !input.trim()}
          style={{ padding: '10px 18px', flexShrink: 0 }}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}