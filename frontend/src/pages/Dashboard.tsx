import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, BalanceSnapshot, Insight, NetWorth } from '../types'
import { TerminalAreaChart, TerminalDonut } from '../components/Chart'
import { simplifyInsightCopy } from '../utils/insightCopy'

const PIE_COLORS = [
  'var(--text)',
  'var(--pos)',
  'var(--accent)',
  'var(--text-2)',
  'var(--text-2)',
  'var(--neg)',
  'var(--text-2)',
]
const RANGE_OPTIONS = ['1M', '3M', '6M', 'YTD', '1Y', 'ALL'] as const

const GROUPS: Array<{ title: string; types: string[] }> = [
  { title: 'Checking & Savings', types: ['checking', 'savings'] },
  { title: 'Investments', types: ['brokerage', '401k', 'roth_ira', 'hsa', 'crypto'] },
  { title: 'Real Estate', types: ['real_estate'] },
  { title: 'Debt', types: ['credit_card', 'student_loan', 'auto_loan', 'personal_loan', 'mortgage'] },
  { title: 'Other', types: ['other'] },
]

function usd(n: number, compact = false) {
  if (compact) {
    const abs = Math.abs(n)
    if (abs >= 1_000) {
      const compactValue = new Intl.NumberFormat('en-US', {
        notation: 'compact',
        maximumFractionDigits: 1,
      }).format(abs).replace('.0', '')
      return `${n < 0 ? '-' : ''}$${compactValue}`
    }
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n)
}

function pct(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return '—'
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('en-US', {
    month: 'numeric',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function stalenessTone(lastUpdated: string | null): 'fresh' | 'aging' | 'stale' {
  if (!lastUpdated) return 'stale'
  const days = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 86_400_000)
  if (days < 7) return 'fresh'
  if (days < 30) return 'aging'
  return 'stale'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const heroShellRef = useRef<HTMLDivElement>(null)
  const [range, setRange] = useState<(typeof RANGE_OPTIONS)[number]>('6M')
  const [heroCollapsed, setHeroCollapsed] = useState<boolean>(() => localStorage.getItem('dashboardHeroCollapsed') === '1')
  const [heroExpandedHeight, setHeroExpandedHeight] = useState(0)
  const [heroCollapsedHeight, setHeroCollapsedHeight] = useState(0)
  const [rotationSeed] = useState<number>(() => Math.floor(Math.random() * 1_000_000))
  const [chatInput, setChatInput] = useState('')
  const [chatReply, setChatReply] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')
  const [now, setNow] = useState(() => new Date())

  const { data: nw, loading: nwLoading, error: nwError } = useApi<NetWorth>(() => api.get('/snapshots/current'), [])
  const { data: history, loading: historyLoading, error: historyError } = useApi<BalanceSnapshot[]>(() => api.get(`/snapshots/net-worth?range=${range}`), [range])
  const { data: accounts, loading: accountsLoading, error: accountsError } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: insights, loading: insightsLoading } = useApi<Insight[]>(() => api.get('/insights'), [])
  const { data: settings } = useApi<Record<string, unknown>>(() => api.get('/settings'), [])

  const groupedAccounts = useMemo(() => {
    const source = [...(accounts ?? [])].sort((a, b) => Math.abs(b.balance) - Math.abs(a.balance))
    return GROUPS.map((group) => ({
      ...group,
      items: source.filter((account) => group.types.includes(account.type)),
    })).filter((group) => group.items.length > 0)
  }, [accounts])

  const recommendation = useMemo(() => {
    if (!insights?.length) return null
    const sorted = [...insights].sort((a, b) => {
      const order = { high: 0, medium: 1, low: 2 }
      return (order[a.priority] ?? 3) - (order[b.priority] ?? 3)
    })
    return sorted[rotationSeed % sorted.length]
  }, [insights, rotationSeed])

  useEffect(() => {
    localStorage.setItem('dashboardHeroCollapsed', heroCollapsed ? '1' : '0')
  }, [heroCollapsed])

  useEffect(() => {
    const node = heroShellRef.current
    if (!node) return

    const measure = () => {
      const h = Math.round(node.getBoundingClientRect().height)
      if (heroCollapsed) {
        setHeroCollapsedHeight((prev) => (h > 0 ? h : prev))
      } else {
        setHeroExpandedHeight((prev) => (h > 0 ? h : prev))
      }
    }

    measure()

    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(measure)
    observer.observe(node)
    return () => observer.disconnect()
  }, [heroCollapsed])

  const allocationData = useMemo(() => {
    if (!nw) return []
    return Object.entries(nw.by_type)
      .filter(([, value]) => value > 0)
      .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }))
      .sort((a, b) => b.value - a.value)
  }, [nw])

  const tone = recommendation?.priority === 'high' ? 'var(--neg)' : recommendation?.priority === 'medium' ? 'var(--accent)' : 'var(--pos)'
  const plainRecommendation = recommendation ? simplifyInsightCopy(recommendation) : null
  const userName = String(settings?.username ?? 'Boss').trim() || 'Boss'

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000)
    return () => window.clearInterval(id)
  }, [])

  const greeting = useMemo(() => {
    const hour = now.getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }, [now])

  const vibeLine = useMemo(() => {
    const dayLines = [
      'Money check-in made simple. Pick one question and we will break it down.',
      'Quick pulse check: ask one thing, get a clear next move.',
      'You are in control. Ask anything about your money in plain English.',
      'Small questions, clear answers, better decisions.',
      'Your numbers are here. Let us make them make sense.',
      'No jargon. Just what is happening and what to do next.',
      'One smart question can save months of confusion.',
      'Clarity first, strategy second. Ask away.',
    ]
    const eveningLines = [
      'Evening check-in: one smart question now, calmer tomorrow.',
      'Wrap the day with one clear money move.',
      'Night mode: simple answers, zero jargon.',
      'End the day with clarity on your next financial step.',
    ]
    const pool = now.getHours() >= 18 ? eveningLines : dayLines
    return pool[Math.floor(Math.random() * pool.length)]
  }, [now])

  const promptPills = [
    'What should I focus on this week?',
    'Am I taking too much risk right now?',
    'What is the fastest win in my finances?',
    'Where is money leaking right now?',
  ]

  async function submitOverviewChat(message?: string) {
    const text = (message ?? chatInput).trim()
    if (!text || chatLoading) return
    setChatError('')
    setChatReply('')
    setChatLoading(true)
    try {
      const { reply } = await api.post<{ reply: string }>('/insights/chat', { message: text })
      setChatReply(reply)
      setChatInput('')
    } catch (e: any) {
      setChatError(e.message?.includes('400') ? 'Claude API key not configured. Add it in Settings.' : e.message)
    } finally {
      setChatLoading(false)
    }
  }

  const historyReady = history && history.length > 0
  const netWorthLoading = nwLoading && !nw
  const historyInitialLoading = historyLoading && !history
  const accountsInitialLoading = accountsLoading && !accounts
  const insightsInitialLoading = insightsLoading && !insights
  const chatCompensation = heroCollapsed && heroExpandedHeight > 0 && heroCollapsedHeight > 0
    ? Math.max(heroExpandedHeight - heroCollapsedHeight, 0)
    : 0

  return (
    <div>
      <div ref={heroShellRef} className={`dashboard-hero-shell mb-24${heroCollapsed ? ' is-collapsed' : ''}`}>
        <button
          type="button"
          className="dashboard-hero-toggle"
          onClick={() => setHeroCollapsed((v) => !v)}
          aria-expanded={!heroCollapsed}
          aria-label={heroCollapsed ? 'Expand net worth and top insight' : 'Collapse net worth and top insight'}
          title={heroCollapsed ? 'Expand overview' : 'Collapse overview'}
        >
          {heroCollapsed ? '▾' : '▴'}
        </button>
        <div className="dashboard-hero-grid">
          <div className="dashboard-hero-summary">
            <div className="section-label mb-8">Total net worth</div>
            <div className="num-hero mb-8">
              {netWorthLoading ? <span className="spinner" aria-label="Loading net worth" style={{ width: 30, height: 30, borderWidth: 3 }} /> : nw ? usd(nw.net_worth) : '$—'}
            </div>

            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', color: 'var(--text-2)', fontSize: 'var(--fs-base)' }}>
              {nwError ? (
                <span style={{ color: 'var(--neg)', fontWeight: 600 }}>Unable to load net worth.</span>
              ) : netWorthLoading ? (
                <span style={{ color: 'var(--text-3)' }}>Loading latest balances…</span>
              ) : (
                <>
                  <span style={{ color: (nw?.delta_30d ?? 0) >= 0 ? 'var(--pos)' : 'var(--neg)', fontWeight: 600 }}>
                    30d: {nw?.delta_30d != null ? `${nw.delta_30d >= 0 ? '+' : ''}${usd(nw.delta_30d)} (${pct(nw.delta_30d_pct)})` : '—'}
                  </span>
                  <span style={{ color: 'var(--text-3)' }}>Last updated: {formatDate(nw?.last_updated)}</span>
                </>
              )}
            </div>
          </div>

          {recommendation ? (
            <div className="dashboard-top-insight" style={{ borderLeftColor: tone }}>
              <div style={{ flex: 1 }}>
                  <div className="section-label mb-8">Top insight</div>
                  <div style={{ fontWeight: 500, fontSize: 'var(--fs-md)', marginBottom: 6 }}>{plainRecommendation?.title ?? recommendation.title}</div>
                  <div style={{ color: 'var(--text-2)', fontSize: 'var(--fs-sm)', lineHeight: 1.55 }}>{plainRecommendation?.description ?? recommendation.description}</div>
                  <div style={{ marginTop: 8, fontSize: 'var(--fs-sm)', color: 'var(--text-3)', lineHeight: 1.5 }}>{plainRecommendation?.action ?? recommendation.action}</div>
              </div>
            </div>
          ) : insightsInitialLoading ? (
            <div style={{ color: 'var(--text-3)', fontSize: 'var(--fs-sm)', fontFamily: 'var(--font-mono)' }}>
              Loading insight…
            </div>
          ) : (
            <div />
          )}
        </div>
      </div>

      <section
        className={`overview-chat-stage mb-24${heroCollapsed ? ' is-expanded' : ''}`}
        style={heroCollapsed ? ({ '--chat-compensation': `${chatCompensation}px` } as Record<string, string>) : undefined}
      >
        <div className="overview-chat-center">
          <h2 className="overview-chat-greeting">{greeting}, {userName}</h2>
          <p className="overview-chat-sub">{vibeLine}</p>
          <div className="overview-chat-prompts">
            {promptPills.map((prompt) => (
              <button
                key={prompt}
                className="overview-chat-prompt"
                onClick={() => { setChatInput(prompt); void submitOverviewChat(prompt) }}
                disabled={chatLoading}
              >
                {prompt}
              </button>
            ))}
          </div>
          {chatReply && (
            <div className="overview-chat-reply">
              {chatReply}
            </div>
          )}
          {chatError && (
            <div className="overview-chat-error">
              {chatError}
            </div>
          )}
        </div>

        <form
          className="overview-chat-composer"
          onSubmit={(e) => {
            e.preventDefault()
            void submitOverviewChat()
          }}
        >
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Ask a question about your finances..."
          />
          <button className="btn btn-primary" type="submit" disabled={chatLoading || !chatInput.trim()}>
            {chatLoading ? 'Thinking...' : 'Ask Claude'}
          </button>
        </form>
      </section>

      <div className="dashboard-top-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 'var(--s-5)', marginBottom: 24 }}>
        <div className="card">
          <div className="flex-between mb-16" style={{ alignItems: 'center' }}>
            <div className="section-label">Net worth history</div>
            <div style={{ display: 'flex', gap: 'var(--s-2)', flexWrap: 'wrap' }}>
              {RANGE_OPTIONS.map((opt) => (
                <button
                  key={opt}
                  className="btn btn-sm"
                  onClick={() => setRange(opt)}
                  style={{
                    padding: '3px 10px',
                    borderColor: opt === range ? 'var(--accent)' : 'var(--border)',
                    color: opt === range ? 'var(--accent)' : 'var(--text-3)',
                  }}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>

          {historyError ? (
            <div className="empty">
              <div className="empty-title">Chart unavailable</div>
              <div className="empty-sub">Net worth history could not be loaded.</div>
            </div>
          ) : historyInitialLoading ? (
            <div className="empty">
              <span className="spinner" aria-label="Loading chart" />
              <div className="empty-sub" style={{ marginTop: 10 }}>Loading net worth history…</div>
            </div>
          ) : historyReady ? (
            <TerminalAreaChart data={history} dataKey="net_worth" height={250} formatter={(value) => usd(value, true)} />
          ) : (
            <div className="empty">
              <div className="empty-title">No chart data</div>
              <div className="empty-sub">Add or import balances to build history.</div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-label mb-16">Allocation (incl. liabilities)</div>
          {nwError ? (
            <div className="empty">
              <div className="empty-title">Allocation unavailable</div>
              <div className="empty-sub">Current balances could not be loaded.</div>
            </div>
          ) : netWorthLoading ? (
            <div className="empty">
              <span className="spinner" aria-label="Loading allocation" />
              <div className="empty-sub" style={{ marginTop: 10 }}>Loading allocation…</div>
            </div>
          ) : allocationData.length > 0 ? (
            <>
              <TerminalDonut data={allocationData} colors={PIE_COLORS} size={170} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-2)', marginTop: 8 }}>
                {allocationData.map((item, i) => (
                  <div key={item.name} className="flex-between" style={{ fontSize: 'var(--fs-sm)' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                      <span style={{ width: 8, height: 8, borderRadius: 'var(--r-round)', background: PIE_COLORS[i % PIE_COLORS.length], display: 'inline-block' }} />
                      <span style={{ textTransform: 'capitalize', color: 'var(--text-2)' }}>{item.name}</span>
                    </div>
                    <span className="num" style={{ fontSize: 'var(--fs-xs)' }}>{usd(item.value, true)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty">
              <div className="empty-sub">No allocation data yet.</div>
            </div>
          )}
        </div>
      </div>

      <div className="card mb-24" style={{ borderColor: 'var(--border)' }}>
        <div className="flex-between mb-16">
          <div>
            <div className="section-label mb-8">Account overview</div>
            <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)' }}>Grouped for fast scanning. Click any account for detail view.</div>
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/accounts')}>Manage accounts</button>
        </div>

        {accountsError ? (
          <div className="empty">
            <div className="empty-title">Accounts unavailable</div>
            <div className="empty-sub">Account balances could not be loaded.</div>
          </div>
        ) : accountsInitialLoading ? (
          <div className="empty">
            <span className="spinner" aria-label="Loading accounts" />
            <div className="empty-sub" style={{ marginTop: 10 }}>Loading accounts…</div>
          </div>
        ) : groupedAccounts.length > 0 ? (
          <table className="tbl">
            <thead>
              <tr>
                <th>Account</th>
                <th>Type</th>
                <th style={{ textAlign: 'right' }}>Balance</th>
                <th style={{ textAlign: 'right' }}>Updated</th>
              </tr>
            </thead>
            <tbody>
              {groupedAccounts.flatMap((group) =>
                group.items.map((account) => {
                  const toneValue = stalenessTone(account.last_updated)
                  const toneColor = toneValue === 'fresh' ? 'var(--pos)' : toneValue === 'aging' ? 'var(--accent)' : 'var(--neg)'
                  return (
                    <tr
                      key={account.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/accounts?accountId=${account.id}`)}
                    >
                      <td style={{ fontWeight: 500 }}>{account.name}</td>
                      <td style={{ color: 'var(--text-3)', textTransform: 'capitalize' }}>{account.type.replace(/_/g, ' ')}</td>
                      <td className="num" style={{ textAlign: 'right' }}>{usd(account.balance)}</td>
                      <td style={{ textAlign: 'right' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)' }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: toneColor, display: 'inline-block', flexShrink: 0 }} />
                          <span className="num" style={{ color: 'var(--text-3)', fontSize: 'var(--fs-xs)' }}>{formatDate(account.last_updated)}</span>
                        </span>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        ) : (
          <div className="empty">
            <div className="empty-title">No accounts yet</div>
            <div className="empty-sub">Add an account in Accounts or import a CSV file.</div>
          </div>
        )}
      </div>

      <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)', marginTop: 8 }}>Local-first. Your data stays here.</div>
    </div>
  )
}
