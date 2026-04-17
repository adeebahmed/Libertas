import { useState, useRef } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Insight } from '../types'

const CAT_CLASS: Record<string, string> = {
  Risk: 'risk', Performance: 'perf', Allocation: 'alloc',
  Liquidity: 'liquid', Trends: 'trend', Retirement: 'retirement',
  Debt: 'debt', Tax: 'tax', Behavioral: 'behavioral', Estate: 'estate',
  info: 'info',
}

const PRIORITY_COLOR: Record<string, string> = {
  high: 'var(--neg)',
  medium: 'var(--accent)',
  low: 'var(--text-3)',
}

type Tab = 'insights' | 'chat'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export default function InsightsPage() {
  const { data: insights, loading, refetch } = useApi<Insight[]>(() => api.get('/insights'), [])
  const [tab, setTab] = useState<Tab>('insights')
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  const filtered = insights?.filter(i => filter === 'all' || i.priority === filter) ?? []
  const highCount = insights?.filter(i => i.priority === 'high').length ?? 0

  const sendChat = async () => {
    const msg = chatInput.trim()
    if (!msg || chatLoading) return
    setChatInput('')
    setChatError('')
    const newMessages: ChatMessage[] = [...chatMessages, { role: 'user', content: msg }]
    setChatMessages(newMessages)
    setChatLoading(true)
    try {
      const { reply } = await api.post<{ reply: string }>('/insights/chat', { message: msg })
      setChatMessages([...newMessages, { role: 'assistant', content: reply }])
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (e: any) {
      setChatError(e.message?.includes('400') ? 'Claude API key not configured. Add it in Settings.' : e.message)
      setChatMessages(newMessages)
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">Insights</h1>

      <div className="tabs mb-24">
        <button className={`tab-btn${tab === 'insights' ? ' active' : ''}`} onClick={() => setTab('insights')}>
          Insights {highCount > 0 && <span style={{ marginLeft: 6, background: 'var(--neg)', color: '#fff', borderRadius: 'var(--r)', padding: '1px 6px', fontSize: 10, fontWeight: 600 }}>{highCount}</span>}
        </button>
        <button className={`tab-btn${tab === 'chat' ? ' active' : ''}`} onClick={() => setTab('chat')}>Ask Claude</button>
      </div>

      {tab === 'insights' && (
        <>
          {/* Priority filter */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            {(['all', 'high', 'medium', 'low'] as const).map(p => (
              <button
                key={p}
                onClick={() => setFilter(p)}
                style={{
                  padding: '4px 12px', borderRadius: 'var(--r-sm)', fontSize: 12, fontWeight: 500,
                  border: `1px solid ${filter === p ? (p === 'all' ? 'var(--border)' : PRIORITY_COLOR[p]) : 'var(--border)'}`,
                  background: filter === p ? 'var(--bg-2)' : 'transparent',
                  color: filter === p ? (p === 'all' ? 'var(--text)' : PRIORITY_COLOR[p]) : 'var(--text-3)',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                }}
              >
                {p}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="empty"><div className="empty-sub">Analysing portfolio…</div></div>
          ) : filtered.length > 0 ? (
            <div className="grid-auto">
              {filtered
                .sort((a, b) => {
                  const order = { high: 0, medium: 1, low: 2 }
                  return (order[a.priority] ?? 3) - (order[b.priority] ?? 3)
                })
                .map((ins, i) => {
                  const cls = CAT_CLASS[ins.category] ?? 'info'
                  return (
                    <div key={i} className={`insight-card ${cls}`}>
                      <div className="flex-between mb-8">
                        <div className="insight-cat">{ins.category}</div>
                        <span style={{
                          fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
                          color: PRIORITY_COLOR[ins.priority] ?? 'var(--text-3)',
                        }}>
                          {ins.priority}
                        </span>
                      </div>
                      <div className="insight-title">{ins.title}</div>
                      <div className="insight-desc">{ins.description}</div>
                      {ins.action && (
                        <div style={{
                          marginTop: 10, padding: '8px 10px',
                          background: 'rgba(59,130,246,0.06)', borderLeft: '2px solid var(--accent)',
                          borderRadius: 'var(--r)', fontSize: 12, color: 'var(--text-2)', lineHeight: 1.5,
                        }}>
                          {ins.action}
                        </div>
                      )}
                      <div className="insight-why">{ins.why}</div>
                    </div>
                  )
                })}
            </div>
          ) : (
            <div className="empty">
              <div className="empty-icon">◌</div>
              <div className="empty-title">{filter === 'all' ? 'No insights yet' : `No ${filter}-priority insights`}</div>
              <div className="empty-sub">Import account data and refresh prices to generate insights</div>
            </div>
          )}
        </>
      )}

      {tab === 'chat' && (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)' }}>
          <div style={{
            flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16,
            padding: '4px 0 16px',
          }}>
            {chatMessages.length === 0 && (
              <div style={{ color: 'var(--text-3)', fontSize: 13, lineHeight: 1.6 }}>
                <div style={{ marginBottom: 12, fontWeight: 500, color: 'var(--text-2)' }}>Ask about your portfolio</div>
                {[
                  'Should I pay off my high-interest debt or invest more?',
                  'Am I on track for retirement?',
                  'What is my biggest financial risk right now?',
                  'How can I reduce my tax bill this year?',
                ].map(q => (
                  <div
                    key={q}
                    onClick={() => setChatInput(q)}
                    style={{
                      padding: '8px 12px', marginBottom: 8, borderRadius: 'var(--r)',
                      border: '1px solid var(--border)', cursor: 'pointer',
                      color: 'var(--text-2)', fontSize: 13,
                    }}
                  >
                    {q}
                  </div>
                ))}
              </div>
            )}
            {chatMessages.map((m, i) => (
              <div key={i} style={{
                alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '80%',
                padding: '10px 14px',
                borderRadius: 'var(--r)',
                background: m.role === 'user' ? 'rgba(59,130,246,0.18)' : 'var(--bg-2)',
                border: '1px solid var(--border)',
                fontSize: 13,
                lineHeight: 1.6,
                color: 'var(--text)',
                whiteSpace: 'pre-wrap',
              }}>
                {m.content}
              </div>
            ))}
            {chatLoading && (
              <div style={{ alignSelf: 'flex-start', color: 'var(--text-3)', fontSize: 13, padding: '10px 14px' }}>
                Thinking…
              </div>
            )}
            {chatError && (
              <div style={{ color: 'var(--neg)', fontSize: 13, padding: '8px 12px', background: 'var(--bg-2)', borderRadius: 'var(--r)' }}>
                {chatError}
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div style={{ display: 'flex', gap: 8, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <input
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendChat()}
              placeholder="Ask about your finances…"
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={sendChat} disabled={chatLoading || !chatInput.trim()}>
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
