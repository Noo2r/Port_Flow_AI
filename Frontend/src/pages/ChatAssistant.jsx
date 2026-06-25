import { useState, useEffect, useRef, useCallback } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { chatApi } from '../services/api'

// ── Markdown renderer ─────────────────────────────────────────────────────────
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

function inlineMarkdown(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(56,189,248,.1);padding:1px 5px;border-radius:3px;font-size:.88em">$1</code>')
    .replace(/✅/g, '<span style="color:#22c55e">✅</span>')
    .replace(/⚠️/g, '<span style="color:#f59e0b">⚠️</span>')
    .replace(/❌/g, '<span style="color:#ef4444">❌</span>')
    .replace(/🔴/g, '<span>🔴</span>')
    .replace(/🔧/g, '<span>🔧</span>')
}

function renderMarkdown(raw) {
  if (!raw) return ''
  const lines = raw.split('\n')
  let html = '', inTable = false, inUl = false, inOl = false, inCode = false, codeBuf = ''

  const closeList = () => {
    if (inUl) { html += '</ul>'; inUl = false }
    if (inOl) { html += '</ol>'; inOl = false }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.startsWith('```')) {
      if (inCode) {
        html += `<pre style="background:rgba(0,0,0,.35);border:1px solid rgba(56,189,248,.12);border-radius:8px;padding:12px 14px;overflow-x:auto;font-size:12.5px;line-height:1.5;margin:10px 0"><code>${esc(codeBuf)}</code></pre>`
        codeBuf = ''; inCode = false
      } else { inCode = true }
      continue
    }
    if (inCode) { codeBuf += line + '\n'; continue }

    const isTableRow = line.includes('|') && line.trim().startsWith('|')
    if (isTableRow) {
      const cells = line.split('|').slice(1, -1).map(c => c.trim())
      const isSep = cells.every(c => /^[-:]+$/.test(c))
      if (!inTable) {
        closeList()
        html += '<div style="overflow-x:auto;margin:10px 0"><table style="width:100%;border-collapse:collapse;font-size:12.5px">'
        html += '<thead><tr>' + cells.map(c => `<th style="padding:7px 12px;text-align:left;color:#38bdf8;border-bottom:1px solid rgba(56,189,248,.2);white-space:nowrap">${inlineMarkdown(c)}</th>`).join('') + '</tr></thead><tbody>'
        inTable = true
      } else if (isSep) {
        /* skip separator row */
      } else {
        html += '<tr>' + cells.map(c => `<td style="padding:6px 12px;border-bottom:1px solid rgba(255,255,255,.05);color:#cbd5e1">${inlineMarkdown(c)}</td>`).join('') + '</tr>'
      }
      continue
    }
    if (inTable) { html += '</tbody></table></div>'; inTable = false }

    if (line.startsWith('### ')) { closeList(); html += `<h3 style="font-size:13.5px;font-weight:700;color:#7dd3fc;margin:12px 0 5px">${inlineMarkdown(line.slice(4))}</h3>`; continue }
    if (line.startsWith('## '))  { closeList(); html += `<h2 style="font-size:15px;font-weight:700;color:#38bdf8;margin:14px 0 6px">${inlineMarkdown(line.slice(3))}</h2>`;  continue }
    if (line.startsWith('# '))   { closeList(); html += `<h1 style="font-size:17px;font-weight:800;color:#e2e8f0;margin:16px 0 8px">${inlineMarkdown(line.slice(2))}</h1>`;   continue }

    const ulMatch = line.match(/^[-*] (.+)/)
    if (ulMatch) {
      if (inOl) { html += '</ol>'; inOl = false }
      if (!inUl) { html += '<ul style="margin:6px 0 6px 18px;padding:0;list-style:none">'; inUl = true }
      html += `<li style="padding:2px 0;color:#cbd5e1">• ${inlineMarkdown(ulMatch[1])}</li>`
      continue
    }
    const olMatch = line.match(/^(\d+)\. (.+)/)
    if (olMatch) {
      if (inUl) { html += '</ul>'; inUl = false }
      if (!inOl) { html += '<ol style="margin:6px 0 6px 20px;padding:0">'; inOl = true }
      html += `<li style="padding:2px 0;color:#cbd5e1">${inlineMarkdown(olMatch[2])}</li>`
      continue
    }

    closeList()
    if (line.trim() === '') { html += '<div style="height:6px"></div>'; continue }
    html += `<p style="margin:3px 0;color:#cbd5e1;line-height:1.55">${inlineMarkdown(line)}</p>`
  }

  if (inTable) html += '</tbody></table></div>'
  closeList()
  if (inCode) html += `<pre style="background:rgba(0,0,0,.35);border-radius:8px;padding:12px 14px;font-size:12.5px"><code>${esc(codeBuf)}</code></pre>`

  return html
}

// ── Suggestion chip ───────────────────────────────────────────────────────────
function SuggestionChip({ text, onClick }) {
  const [hover, setHover] = useState(false)
  return (
    <button
      onClick={() => onClick(text)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: '5px 11px', borderRadius: 20, fontSize: 11.5, cursor: 'pointer',
        border: '1px solid rgba(56,189,248,.25)',
        background: hover ? 'rgba(56,189,248,.12)' : 'rgba(56,189,248,.05)',
        color: hover ? '#7dd3fc' : '#64748b',
        transition: 'all .15s', fontFamily: 'Inter,sans-serif',
        whiteSpace: 'nowrap',
      }}
    >
      {text}
    </button>
  )
}

// ── Tool badge ────────────────────────────────────────────────────────────────
const TOOL_ICONS = {
  get_port_kpis:          { icon: 'fa-chart-line',   label: 'Port KPIs' },
  get_berth_status:       { icon: 'fa-anchor',        label: 'Berth Status' },
  list_vessels:           { icon: 'fa-ship',          label: 'Vessel List' },
  list_upcoming_arrivals: { icon: 'fa-calendar-day',  label: 'Arrivals' },
  get_congestion_forecast:{ icon: 'fa-water',         label: 'Congestion AI' },
  get_port_allocations:   { icon: 'fa-table',         label: 'Allocations' },
  get_vessel_history:     { icon: 'fa-clock-rotate-left', label: 'Vessel History' },
  get_analytics:          { icon: 'fa-chart-column',  label: 'Analytics' },
  list_notifications:     { icon: 'fa-bell',          label: 'Alerts' },
}

function ToolBadge({ name }) {
  const meta = TOOL_ICONS[name] || { icon: 'fa-database', label: name }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 7px', borderRadius: 10, fontSize: 10,
      background: 'rgba(56,189,248,.08)', border: '1px solid rgba(56,189,248,.15)',
      color: '#38bdf8', marginRight: 4, marginBottom: 3, fontFamily: 'Inter,sans-serif',
    }}>
      <i className={`fa-solid ${meta.icon}`} style={{ fontSize: 9 }} />
      {meta.label}
    </span>
  )
}

// ── Message bubble ────────────────────────────────────────────────────────────
function MessageBubble({ msg, onSuggestion }) {
  const [copied, setCopied] = useState(false)
  const isUser = msg.role === 'user'

  const copyText = () => {
    navigator.clipboard?.writeText(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div style={{
      display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-start', gap: 10, marginBottom: 18,
    }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: 9, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13,
        background: isUser
          ? 'linear-gradient(135deg,#1d4ed8,#0891b2)'
          : 'linear-gradient(135deg,#1e3a5f,#0c4a6e)',
        border: isUser ? 'none' : '1px solid rgba(56,189,248,.25)',
        boxShadow: isUser ? '0 0 12px rgba(29,78,216,.4)' : '0 0 12px rgba(56,189,248,.2)',
        marginTop: 2,
      }}>
        {isUser
          ? <i className="fa-solid fa-user" style={{ color: '#bfdbfe' }} />
          : <i className="fa-solid fa-anchor" style={{ color: '#38bdf8' }} />
        }
      </div>

      {/* Bubble */}
      <div style={{ maxWidth: '82%', minWidth: 80 }}>
        <div style={{
          padding: '11px 14px',
          borderRadius: isUser ? '14px 4px 14px 14px' : '4px 14px 14px 14px',
          background: isUser
            ? 'linear-gradient(135deg,rgba(29,78,216,.35),rgba(8,145,178,.25))'
            : 'rgba(6,17,31,.8)',
          border: isUser
            ? '1px solid rgba(29,78,216,.4)'
            : '1px solid rgba(56,189,248,.12)',
          position: 'relative',
        }}>
          {isUser ? (
            <p style={{ margin: 0, color: '#dbeafe', fontSize: 13.5, lineHeight: 1.5, fontFamily: 'Inter,sans-serif' }}>
              {msg.content}
            </p>
          ) : (
            <div
              style={{ fontSize: 13, fontFamily: 'Inter,sans-serif' }}
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
            />
          )}

          {/* Copy button on assistant messages */}
          {!isUser && (
            <button
              onClick={copyText}
              style={{
                position: 'absolute', top: 8, right: 8,
                background: 'none', border: 'none', cursor: 'pointer',
                color: copied ? '#22c55e' : '#334155', fontSize: 11,
                padding: '2px 5px', borderRadius: 5, transition: 'color .15s',
              }}
              title="Copy"
            >
              <i className={`fa-solid ${copied ? 'fa-check' : 'fa-copy'}`} />
            </button>
          )}
        </div>

        {/* Tool calls used */}
        {msg.toolCalls?.length > 0 && (
          <div style={{ marginTop: 5, display: 'flex', flexWrap: 'wrap' }}>
            {msg.toolCalls.map(t => <ToolBadge key={t} name={t} />)}
          </div>
        )}

        {/* Model badge */}
        {msg.modelUsed && msg.modelUsed !== 'rule-based' && (
          <div style={{ marginTop: 4, fontSize: 10, color: '#1e3a5f', fontFamily: 'monospace' }}>
            {msg.modelUsed.replace('claude-', '').replace(/-\d+$/, '')}
          </div>
        )}

        {/* Suggestions */}
        {msg.suggestions?.length > 0 && (
          <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            {msg.suggestions.map(s => (
              <SuggestionChip key={s} text={s} onClick={onSuggestion} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Typing indicator ──────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 18 }}>
      <div style={{
        width: 32, height: 32, borderRadius: 9, flexShrink: 0, marginTop: 2,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'linear-gradient(135deg,#1e3a5f,#0c4a6e)',
        border: '1px solid rgba(56,189,248,.25)',
      }}>
        <i className="fa-solid fa-anchor" style={{ color: '#38bdf8', fontSize: 13 }} />
      </div>
      <div style={{
        padding: '12px 16px', borderRadius: '4px 14px 14px 14px',
        background: 'rgba(6,17,31,.8)', border: '1px solid rgba(56,189,248,.12)',
        display: 'flex', gap: 5, alignItems: 'center',
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 7, height: 7, borderRadius: '50%', background: '#38bdf8',
            animation: 'chatBounce .9s ease-in-out infinite',
            animationDelay: `${i * 0.15}s`,
          }} />
        ))}
      </div>
    </div>
  )
}

// ── Welcome screen ────────────────────────────────────────────────────────────
function WelcomeScreen({ onSuggestion, defaultSuggestions }) {
  const panels = [
    { icon: 'fa-chart-line',   color: '#3b82f6', title: 'Port KPIs',    desc: 'Live utilization, wait times, throughputs' },
    { icon: 'fa-water',        color: '#06b6d4', title: 'Congestion AI', desc: '24–72h AI-powered traffic forecast' },
    { icon: 'fa-ship',         color: '#22c55e', title: 'Vessel Tracker', desc: 'Fleet status, arrivals, history' },
    { icon: 'fa-anchor',       color: '#f59e0b', title: 'Berth Manager', desc: 'Occupancy, conflicts, allocations' },
  ]
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px 20px', gap: 24 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{
          width: 56, height: 56, borderRadius: 16, margin: '0 auto 14px',
          background: 'linear-gradient(135deg,#1d4ed8,#0891b2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 28px rgba(29,78,216,.45)',
        }}>
          <i className="fa-solid fa-anchor" style={{ color: '#fff', fontSize: 22 }} />
        </div>
        <h2 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 800, color: '#e2e8f0', fontFamily: 'Inter,sans-serif' }}>
          PortFlow AI Assistant
        </h2>
        <p style={{ margin: 0, fontSize: 12.5, color: '#475569', fontFamily: 'Inter,sans-serif' }}>
          Ask anything about port operations · I have live access to all systems
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, width: '100%', maxWidth: 480 }}>
        {panels.map(p => (
          <div key={p.title} style={{
            padding: '12px 14px', borderRadius: 10,
            background: 'rgba(6,17,31,.7)', border: '1px solid rgba(255,255,255,.06)',
            display: 'flex', alignItems: 'flex-start', gap: 10,
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: 7, flexShrink: 0,
              background: `${p.color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <i className={`fa-solid ${p.icon}`} style={{ color: p.color, fontSize: 12 }} />
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#e2e8f0', fontFamily: 'Inter,sans-serif' }}>{p.title}</div>
              <div style={{ fontSize: 10.5, color: '#475569', fontFamily: 'Inter,sans-serif', marginTop: 2 }}>{p.desc}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ width: '100%', maxWidth: 560 }}>
        <p style={{ margin: '0 0 10px', fontSize: 11, color: '#334155', textAlign: 'center', fontFamily: 'Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '1px' }}>
          Quick start
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, justifyContent: 'center' }}>
          {defaultSuggestions.map(s => <SuggestionChip key={s} text={s} onClick={onSuggestion} />)}
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ChatAssistant() {
  const [messages,    setMessages]    = useState([])
  const [input,       setInput]       = useState('')
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState(null)
  const [defaultSugg, setDefaultSugg] = useState([
    "What are the current port KPIs?",
    "Show congestion forecast for 48 hours",
    "Which vessels are arriving today?",
    "Show berth utilization status",
    "Are there any scheduling conflicts?",
    "List vessels that are anchored",
    "Which berth has highest utilization?",
    "Show recent system alerts",
  ])

  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)
  const textareaRef = useRef(null)

  // Fetch default suggestions on mount
  useEffect(() => {
    chatApi.suggestions()
      .then(d => { if (d?.suggestions) setDefaultSugg(d.suggestions) })
      .catch(() => {})
  }, [])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 140) + 'px'
  }, [input])

  const send = useCallback(async (text) => {
    const msg = (text || input).trim()
    if (!msg || loading) return

    setInput('')
    setError(null)

    const userMsg = { role: 'user', content: msg, id: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    // Build history for the API (text-only, last 10 turns)
    const history = messages.slice(-10).map(m => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const data = await chatApi.message(msg, history)
      setMessages(prev => [
        ...prev,
        {
          role:        'assistant',
          content:     data.response,
          suggestions: data.suggested_questions,
          toolCalls:   data.tool_calls_made,
          modelUsed:   data.model_used,
          id:          Date.now() + 1,
        },
      ])
    } catch (err) {
      setError(err.message)
      setMessages(prev => [
        ...prev,
        {
          role:    'assistant',
          content: `⚠️ **Error:** ${err.message}\n\nPlease check the backend is running and try again.`,
          id:      Date.now() + 1,
        },
      ])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [input, loading, messages])

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const clearChat = () => { setMessages([]); setError(null); inputRef.current?.focus() }

  const panelBg = 'rgba(3,7,16,.95)'

  return (
    <MainLayout>
      <style>{`
        @keyframes chatBounce {
          0%,80%,100% { transform:translateY(0) }
          40%          { transform:translateY(-5px) }
        }
        .chat-input-area:focus-within { border-color:rgba(56,189,248,.4) !important; box-shadow:0 0 0 3px rgba(56,189,248,.08) !important; }
      `}</style>

      <Navbar
        title="AI Port Assistant"
        subtitle="Natural language operations queries · live data · context retention"
      />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', background: '#030710' }}>

        {/* ── Chat column ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px 22px 8px', scrollbarWidth: 'thin' }}>
            {messages.length === 0 ? (
              <WelcomeScreen onSuggestion={send} defaultSuggestions={defaultSugg} />
            ) : (
              <>
                {messages.map(msg => (
                  <MessageBubble key={msg.id} msg={msg} onSuggestion={send} />
                ))}
                {loading && <TypingIndicator />}
                <div ref={bottomRef} />
              </>
            )}
          </div>

          {/* Input area */}
          <div style={{ padding: '12px 22px 18px', borderTop: '1px solid rgba(148,163,184,.07)', background: panelBg }}>
            <div
              className="chat-input-area"
              style={{
                display: 'flex', alignItems: 'flex-end', gap: 10,
                background: 'rgba(6,17,31,.9)',
                border: '1px solid rgba(56,189,248,.14)',
                borderRadius: 14, padding: '10px 12px 10px 16px',
                transition: 'border-color .2s, box-shadow .2s',
              }}
            >
              <textarea
                ref={el => { textareaRef.current = el; inputRef.current = el }}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about port operations, vessels, berths, congestion…"
                disabled={loading}
                rows={1}
                style={{
                  flex: 1, background: 'none', border: 'none', outline: 'none', resize: 'none',
                  color: '#e2e8f0', fontSize: 13.5, fontFamily: 'Inter,sans-serif',
                  lineHeight: 1.5, overflowY: 'hidden',
                  scrollbarWidth: 'none', caretColor: '#38bdf8',
                }}
              />
              <div style={{ display: 'flex', gap: 7, flexShrink: 0 }}>
                {messages.length > 0 && (
                  <button
                    onClick={clearChat}
                    title="Clear conversation"
                    style={{
                      width: 34, height: 34, borderRadius: 9,
                      background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)',
                      color: '#475569', cursor: 'pointer', fontSize: 13, display: 'flex',
                      alignItems: 'center', justifyContent: 'center', transition: 'all .15s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color='#94a3b8'; e.currentTarget.style.borderColor='rgba(255,255,255,.15)' }}
                    onMouseLeave={e => { e.currentTarget.style.color='#475569'; e.currentTarget.style.borderColor='rgba(255,255,255,.08)' }}
                  >
                    <i className="fa-solid fa-trash-can" />
                  </button>
                )}
                <button
                  onClick={() => send()}
                  disabled={!input.trim() || loading}
                  style={{
                    width: 34, height: 34, borderRadius: 9, cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
                    background: input.trim() && !loading ? 'linear-gradient(135deg,#1d4ed8,#0891b2)' : 'rgba(255,255,255,.04)',
                    border: '1px solid ' + (input.trim() && !loading ? 'rgba(56,189,248,.3)' : 'rgba(255,255,255,.08)'),
                    color: input.trim() && !loading ? '#fff' : '#2a3f66',
                    fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'all .15s',
                    boxShadow: input.trim() && !loading ? '0 0 14px rgba(29,78,216,.4)' : 'none',
                  }}
                >
                  {loading
                    ? <i className="fa-solid fa-circle-notch fa-spin" style={{ fontSize: 12 }} />
                    : <i className="fa-solid fa-paper-plane" />
                  }
                </button>
              </div>
            </div>
            <div style={{ marginTop: 6, fontSize: 10.5, color: '#1e3a5f', fontFamily: 'Inter,sans-serif', textAlign: 'center' }}>
              Enter to send · Shift+Enter for new line · Data is live from the port database
            </div>
          </div>
        </div>

        {/* ── Right sidebar: context panel ── */}
        <div style={{
          width: 230, flexShrink: 0, borderLeft: '1px solid rgba(148,163,184,.07)',
          background: panelBg, display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{ padding: '16px 14px 12px', borderBottom: '1px solid rgba(148,163,184,.07)' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#38bdf8', letterSpacing: '1.5px', textTransform: 'uppercase', marginBottom: 3, fontFamily: 'monospace' }}>
              Quick Actions
            </div>
          </div>

          {/* Action groups */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px', scrollbarWidth: 'thin' }}>
            {[
              {
                label: 'Operations',
                items: [
                  { icon: 'fa-chart-line',  text: 'Port KPIs',          q: 'What are the current port KPIs?' },
                  { icon: 'fa-anchor',      text: 'Berth Status',        q: 'Show me the status of all berths' },
                  { icon: 'fa-table',       text: 'Allocations',         q: 'Show current berth allocations' },
                  { icon: 'fa-triangle-exclamation', text: 'Conflicts',  q: 'Are there any scheduling conflicts?' },
                ],
              },
              {
                label: 'Vessels',
                items: [
                  { icon: 'fa-ship',             text: 'All Vessels',  q: 'Show me all vessels in the fleet' },
                  { icon: 'fa-calendar-day',     text: 'Arriving Today', q: 'Which vessels are arriving today?' },
                  { icon: 'fa-clock',            text: 'Anchored/Waiting', q: 'List all vessels currently anchored or waiting' },
                  { icon: 'fa-clock-rotate-left',text: 'Recent History', q: 'Show recent vessel visit history' },
                ],
              },
              {
                label: 'Intelligence',
                items: [
                  { icon: 'fa-water',       text: '48h Forecast',   q: 'Predict congestion for the next 48 hours' },
                  { icon: 'fa-water',       text: '72h Forecast',   q: 'Show congestion forecast for 72 hours' },
                  { icon: 'fa-chart-column',text: 'Analytics',      q: 'Show port analytics and performance trends' },
                  { icon: 'fa-bell',        text: 'Recent Alerts',  q: 'Show me recent system notifications and alerts' },
                ],
              },
            ].map(grp => (
              <div key={grp.label} style={{ marginBottom: 18 }}>
                <div style={{ fontSize: 9.5, fontWeight: 700, color: '#334155', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: 6, fontFamily: 'Inter,sans-serif' }}>
                  {grp.label}
                </div>
                {grp.items.map(item => (
                  <ActionButton key={item.q} icon={item.icon} text={item.text} onClick={() => send(item.q)} />
                ))}
              </div>
            ))}
          </div>

          {/* Conversation stats */}
          <div style={{ padding: '10px 14px', borderTop: '1px solid rgba(148,163,184,.07)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10.5, color: '#334155', fontFamily: 'Inter,sans-serif' }}>
              <span>Messages</span>
              <span style={{ color: '#475569' }}>{messages.length}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10.5, color: '#334155', fontFamily: 'Inter,sans-serif', marginTop: 3 }}>
              <span>Tools used</span>
              <span style={{ color: '#475569' }}>
                {[...new Set(messages.flatMap(m => m.toolCalls || []))].length}
              </span>
            </div>
            {messages.length > 0 && (
              <button
                onClick={clearChat}
                style={{
                  marginTop: 8, width: '100%', padding: '5px 0',
                  background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.15)',
                  color: '#64748b', borderRadius: 7, cursor: 'pointer', fontSize: 11,
                  fontFamily: 'Inter,sans-serif', transition: 'all .15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.color='#fb7185'; e.currentTarget.style.borderColor='rgba(239,68,68,.3)' }}
                onMouseLeave={e => { e.currentTarget.style.color='#64748b'; e.currentTarget.style.borderColor='rgba(239,68,68,.15)' }}
              >
                <i className="fa-solid fa-trash-can" style={{ marginRight: 5 }} />Clear Chat
              </button>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  )
}

// ── Sidebar action button ──────────────────────────────────────────────────────
function ActionButton({ icon, text, onClick }) {
  const [hover, setHover] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 8, width: '100%',
        padding: '6px 8px', borderRadius: 7, marginBottom: 2,
        background: hover ? 'rgba(56,189,248,.08)' : 'transparent',
        border: '1px solid ' + (hover ? 'rgba(56,189,248,.15)' : 'transparent'),
        color: hover ? '#7dd3fc' : '#334155',
        cursor: 'pointer', fontSize: 11.5, fontFamily: 'Inter,sans-serif',
        transition: 'all .12s', textAlign: 'left',
      }}
    >
      <i className={`fa-solid ${icon}`} style={{ width: 12, fontSize: 10.5, flexShrink: 0 }} />
      {text}
    </button>
  )
}
