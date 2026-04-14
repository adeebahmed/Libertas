import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, BalanceSnapshot, Insight, NetWorth } from '../types'
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const PIE_COLORS = ['#3b82f6', '#34d399', '#d4a840', '#a78bfa', '#22d3ee', '#f87171', '#60a5fa']
const RANGE_OPTIONS = ['1M', '3M', '6M', 'YTD', '1Y', 'ALL'] as const

const GROUPS: Array<{ title: string; types: string[] }> = [
  { title: 'Checking & Savings', types: ['checking', 'savings'] },
  { title: 'Investments', types: ['brokerage', '401k', 'roth_ira', 'hsa', 'crypto'] },
  { title: 'Real Estate', types: ['real_estate'] },
  { title: 'Debt', types: ['credit_card', 'student_loan', 'auto_loan', 'personal_loan', 'mortgage'] },
  { title: 'Other', types: ['other'] },
]

function usd(n: number, compact = false) {
  if (compact && Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (compact && Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}k`
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
  return d.toLocaleString()
}

function stalenessTone(lastUpdated: string | null): 'green' | 'gold' | 'red' {
  if (!lastUpdated) return 'red'
  const days = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 86_400_000)
  if (days < 7) return 'green'
  if (days < 30) return 'gold'
  return 'red'
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: '10px 12px',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
      }}
    >
      <div style={{ color: 'var(--text-3)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: 'var(--text)' }}>{usd(payload[0].value)}</div>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [range, setRange] = useState<(typeof RANGE_OPTIONS)[number]>('6M')
  const [pinnedTitle, setPinnedTitle] = useState<string | null>(() => localStorage.getItem('dashboardPinnedInsight'))
  const [rotationSeed] = useState<number>(() => Math.floor(Math.random() * 1_000_000))

  const { data: nw } = useApi<NetWorth>(() => api.get('/snapshots/current'), [])
  const { data: history } = useApi<BalanceSnapshot[]>(() => api.get(`/snapshots/net-worth?range=${range}`), [range])
  const { data: accounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: insights } = useApi<Insight[]>(() => api.get('/insights'), [])

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

    if (pinnedTitle) {
      const pinned = sorted.find((item) => item.title === pinnedTitle)
      if (pinned) return pinned
    }

    return sorted[rotationSeed % sorted.length]
  }, [insights, pinnedTitle, rotationSeed])

  useEffect(() => {
    if (!pinnedTitle) {
      localStorage.removeItem('dashboardPinnedInsight')
      return
    }
    localStorage.setItem('dashboardPinnedInsight', pinnedTitle)
  }, [pinnedTitle])

  const allocationData = useMemo(() => {
    if (!nw) return []
    return Object.entries(nw.by_type)
      .filter(([, value]) => value > 0)
      .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }))
      .sort((a, b) => b.value - a.value)
  }, [nw])

  const tone = recommendation?.priority === 'high' ? 'var(--red)' : recommendation?.priority === 'medium' ? 'var(--gold)' : 'var(--green)'

  const historyReady = history && history.length > 0

  return (
    <div>
      <div className="mb-24" style={{ paddingBottom: 24, borderBottom: '1px solid var(--border)' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 20,
            alignItems: 'start',
          }}
        >
          <div>
            <div className="section-label mb-8">Total net worth</div>
            <div className="num-hero mb-8">{nw ? usd(nw.net_worth) : '$—'}</div>

            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', color: 'var(--text-2)', fontSize: 13 }}>
              <span style={{ color: (nw?.delta_30d ?? 0) >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                30d: {nw?.delta_30d != null ? `${nw.delta_30d >= 0 ? '+' : ''}${usd(nw.delta_30d)} (${pct(nw.delta_30d_pct)})` : '—'}
              </span>
              <span style={{ color: 'var(--text-3)' }}>Last updated: {formatDate(nw?.last_updated)}</span>
            </div>
          </div>

          {recommendation ? (
            <div className="card" style={{ borderColor: `${tone}55`, borderLeft: `3px solid ${tone}`, marginBottom: 0 }}>
              <div className="flex-between" style={{ alignItems: 'start', gap: 10 }}>
                <div>
                  <div className="section-label mb-8">Top recommendation</div>
                  <div style={{ fontWeight: 600, fontSize: 17, marginBottom: 6 }}>{recommendation.title}</div>
                  <div style={{ color: 'var(--text-2)', fontSize: 13, lineHeight: 1.55 }}>{recommendation.description}</div>
                  <div style={{ marginTop: 10, fontSize: 13, color: 'var(--text)', lineHeight: 1.5 }}>{recommendation.action}</div>
                </div>
                <button
                  className="btn btn-sm"
                  onClick={() => setPinnedTitle((curr) => (curr === recommendation.title ? null : recommendation.title))}
                  title="Pin recommendation"
                >
                  {pinnedTitle === recommendation.title ? 'Unpin' : 'Pin'}
                </button>
              </div>
            </div>
          ) : (
            <div />
          )}
        </div>
      </div>

      <div className="dashboard-top-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20, marginBottom: 24 }}>
        <div className="card">
          <div className="flex-between mb-16" style={{ alignItems: 'center' }}>
            <div className="section-label">Net worth history</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {RANGE_OPTIONS.map((opt) => (
                <button
                  key={opt}
                  className="btn btn-sm"
                  onClick={() => setRange(opt)}
                  style={{
                    padding: '3px 10px',
                    borderColor: opt === range ? 'var(--blue)' : 'var(--border-soft)',
                    color: opt === range ? 'var(--blue-bright)' : 'var(--text-3)',
                  }}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>

          {historyReady ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={history} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fill: 'var(--text-3)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(value) => usd(value, true)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="net_worth" stroke="#3b82f6" strokeWidth={1.6} fill="url(#blueGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty">
              <div className="empty-title">No chart data</div>
              <div className="empty-sub">Add or import balances to build history.</div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-label mb-16">Allocation (incl. liabilities)</div>
          {allocationData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={170}>
                <PieChart>
                  <Pie data={allocationData} dataKey="value" cx="50%" cy="50%" innerRadius={50} outerRadius={76} paddingAngle={2}>
                    {allocationData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                {allocationData.map((item, i) => (
                  <div key={item.name} className="flex-between" style={{ fontSize: 12 }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                      <span style={{ width: 8, height: 8, borderRadius: 999, background: PIE_COLORS[i % PIE_COLORS.length], display: 'inline-block' }} />
                      <span style={{ textTransform: 'capitalize', color: 'var(--text-2)' }}>{item.name}</span>
                    </div>
                    <span className="num" style={{ fontSize: 11 }}>{usd(item.value, true)}</span>
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

      <div className="card mb-24" style={{ borderColor: 'var(--border-soft)' }}>
        <div className="flex-between mb-16">
          <div>
            <div className="section-label mb-8">Account overview</div>
            <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>Grouped for fast scanning. Click any account for detail view.</div>
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/accounts')}>Quick add</button>
        </div>

        {groupedAccounts.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {groupedAccounts.map((group) => (
              <div key={group.title}>
                <div style={{ marginBottom: 8, color: 'var(--text-3)', fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase' }}>
                  {group.title}
                </div>
                <div className="grid-auto" style={{ gap: 10 }}>
                  {group.items.map((account) => {
                    const toneValue = stalenessTone(account.last_updated)
                    const toneColor = toneValue === 'green' ? 'var(--green)' : toneValue === 'gold' ? 'var(--gold)' : 'var(--red)'

                    return (
                      <button
                        key={account.id}
                        className="card"
                        onClick={() => navigate(`/accounts?accountId=${account.id}`)}
                        style={{
                          textAlign: 'left',
                          padding: '14px 16px',
                          display: 'grid',
                          gridTemplateColumns: '1fr auto',
                          gap: 12,
                          alignItems: 'center',
                          color: 'var(--text)',
                          font: 'inherit',
                          background: 'linear-gradient(135deg, rgba(255,255,255,0.015), rgba(255,255,255,0.005))',
                          border: '1px solid var(--border-soft)',
                          borderRadius: 12,
                          cursor: 'pointer',
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>{account.name}</div>
                          <div style={{ color: 'var(--text-3)', fontSize: 12, textTransform: 'capitalize' }}>{account.type.replace(/_/g, ' ')}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div className="num" style={{ fontSize: 14 }}>{usd(account.balance)}</div>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-3)', marginTop: 3 }}>
                            <span style={{ width: 7, height: 7, borderRadius: 999, background: toneColor, display: 'inline-block' }} />
                            {formatDate(account.last_updated)}
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty">
            <div className="empty-title">No accounts yet</div>
            <div className="empty-sub">Add an account in Accounts or import a CSV file.</div>
          </div>
        )}
      </div>

      <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 8 }}>Local-first. Your data stays here.</div>
    </div>
  )
}
