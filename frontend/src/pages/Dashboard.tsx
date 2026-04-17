import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, BalanceSnapshot, Insight, NetWorth } from '../types'
import { TerminalAreaChart, TerminalDonut } from '../components/Chart'

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

function stalenessTone(lastUpdated: string | null): 'fresh' | 'aging' | 'stale' {
  if (!lastUpdated) return 'stale'
  const days = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 86_400_000)
  if (days < 7) return 'fresh'
  if (days < 30) return 'aging'
  return 'stale'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [range, setRange] = useState<(typeof RANGE_OPTIONS)[number]>('6M')
  const [pinnedTitle, setPinnedTitle] = useState<string | null>(() => localStorage.getItem('dashboardPinnedInsight'))
  const [rotationSeed] = useState<number>(() => Math.floor(Math.random() * 1_000_000))

  const { data: nw, loading: nwLoading, error: nwError } = useApi<NetWorth>(() => api.get('/snapshots/current'), [])
  const { data: history, loading: historyLoading, error: historyError } = useApi<BalanceSnapshot[]>(() => api.get(`/snapshots/net-worth?range=${range}`), [range])
  const { data: accounts, loading: accountsLoading, error: accountsError } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: insights, loading: insightsLoading } = useApi<Insight[]>(() => api.get('/insights'), [])

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

  const tone = recommendation?.priority === 'high' ? 'var(--neg)' : recommendation?.priority === 'medium' ? 'var(--accent)' : 'var(--pos)'

  const historyReady = history && history.length > 0
  const netWorthLoading = nwLoading && !nw
  const historyInitialLoading = historyLoading && !history
  const accountsInitialLoading = accountsLoading && !accounts
  const insightsInitialLoading = insightsLoading && !insights

  return (
    <div>
      <div className="mb-24" style={{ paddingBottom: 24, borderBottom: '1px solid var(--border)' }}>
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
            <div style={{ borderLeft: `2px solid ${tone}`, paddingLeft: 'var(--s-4)', marginBottom: 0 }}>
              <div className="flex-between" style={{ alignItems: 'start', gap: 'var(--s-2)' }}>
                <div>
                  <div className="section-label mb-8">Top insight</div>
                  <div style={{ fontWeight: 500, fontSize: 'var(--fs-md)', marginBottom: 6 }}>{recommendation.title}</div>
                  <div style={{ color: 'var(--text-2)', fontSize: 'var(--fs-sm)', lineHeight: 1.55 }}>{recommendation.description}</div>
                  <div style={{ marginTop: 8, fontSize: 'var(--fs-sm)', color: 'var(--text-3)', lineHeight: 1.5 }}>{recommendation.action}</div>
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
          ) : insightsInitialLoading ? (
            <div style={{ color: 'var(--text-3)', fontSize: 'var(--fs-sm)', fontFamily: 'var(--font-mono)' }}>
              Loading insight…
            </div>
          ) : (
            <div />
          )}
        </div>
      </div>

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
