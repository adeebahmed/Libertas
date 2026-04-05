import { useEffect, useMemo, useRef, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { NetWorth, BalanceSnapshot, Account, NewsArticle } from '../types'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'

const PIE_COLORS = ['#c9a96e', '#5cad7a', '#6a9fc0', '#c95f52', '#9b85c4', '#e0906a', '#5bbfbf', '#9bc87a']
const NEWS_GLASS_TINTS = [
  'rgba(201, 169, 110, 0.10)',
  'rgba(106, 159, 192, 0.11)',
  'rgba(92, 173, 122, 0.10)',
  'rgba(155, 133, 196, 0.11)',
  'rgba(224, 144, 106, 0.11)',
  'rgba(91, 191, 191, 0.10)',
]

function usd(n: number, compact = false) {
  if (compact && Math.abs(n) >= 1_000_000)
    return `$${(n / 1_000_000).toFixed(2)}M`
  if (compact && Math.abs(n) >= 1_000)
    return `$${(n / 1_000).toFixed(1)}k`
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function pct(n: number, total: number) {
  return total ? ((n / total) * 100).toFixed(1) + '%' : '—'
}

function timeAgo(iso: string | null): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 1) return 'just now'
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1c1a14', border: '1px solid #26231b', borderRadius: 8,
      padding: '10px 14px', fontFamily: 'var(--font-mono)', fontSize: 12,
    }}>
      <div style={{ color: '#5c5444', marginBottom: 4 }}>{label}</div>
      <div style={{ color: '#f0ebe2' }}>{usd(payload[0].value)}</div>
    </div>
  )
}

export default function Dashboard() {
  const accountsColRef = useRef<HTMLDivElement | null>(null)
  const [accountsColHeight, setAccountsColHeight] = useState<number | null>(null)
  const newsPath = useMemo(() => {
    let shouldRefresh = false
    try {
      const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined
      shouldRefresh = nav?.type === 'reload'
    } catch {}
    return `/news?limit=8${shouldRefresh ? '&refresh=1' : ''}`
  }, [])

  const { data: nw }       = useApi<NetWorth>(() => api.get('/snapshots/current'), [])
  const { data: history }  = useApi<BalanceSnapshot[]>(() => api.get('/snapshots/net-worth'), [])
  const { data: accounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: news, loading: newsLoading } = useApi<NewsArticle[]>(() => api.get(newsPath), [newsPath])

  const allocationData = nw
    ? Object.entries(nw.by_type)
        .filter(([, v]) => v > 0)
        .map(([name, value]) => ({ name: name.replace('_', ' '), value }))
        .sort((a, b) => b.value - a.value)
    : []

  const totalBalance = accounts?.reduce((s, a) => s + a.balance, 0) ?? 0
  const deltaSign = (nw?.delta ?? 0) >= 0

  useEffect(() => {
    const el = accountsColRef.current
    if (!el || typeof ResizeObserver === 'undefined') return

    const update = () => setAccountsColHeight(Math.round(el.getBoundingClientRect().height))
    update()

    const observer = new ResizeObserver(update)
    observer.observe(el)
    window.addEventListener('resize', update)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', update)
    }
  }, [accounts?.length])

  return (
    <div>
      {/* Hero net worth */}
      <div className="mb-32" style={{ paddingBottom: 32, borderBottom: '1px solid var(--border)' }}>
        <div className="section-label mb-8">Total net worth</div>
        <div className="num-hero mb-8">
          {nw ? usd(nw.net_worth) : '$—'}
        </div>
        {nw && nw.delta !== 0 && (
          <div className={deltaSign ? 'delta-up' : 'delta-down'}>
            {deltaSign ? '↑' : '↓'} {usd(Math.abs(nw.delta))} since last snapshot
          </div>
        )}
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20, marginBottom: 32 }}>
        {/* Net worth timeline */}
        <div className="card">
          <div className="section-label mb-16">Portfolio growth</div>
          {history && history.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={history} margin={{ top: 4, right: 4, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"   stopColor="#c9a96e" stopOpacity={0.25} />
                    <stop offset="95%"  stopColor="#c9a96e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fill: '#5c5444', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fill: '#5c5444', fontSize: 11 }}
                  axisLine={false} tickLine={false}
                  tickFormatter={(v) => usd(v, true)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone" dataKey="net_worth"
                  stroke="#c9a96e" strokeWidth={1.5}
                  fill="url(#goldGrad)" dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty">
              <div className="empty-icon">◌</div>
              <div className="empty-title">No history yet</div>
              <div className="empty-sub">Import data to track growth over time</div>
            </div>
          )}
        </div>

        {/* Allocation donut */}
        <div className="card">
          <div className="section-label mb-16">Allocation</div>
          {allocationData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={allocationData}
                    cx="50%" cy="50%"
                    innerRadius={50} outerRadius={75}
                    dataKey="value" strokeWidth={0}
                    paddingAngle={2}
                  >
                    {allocationData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) =>
                      active && payload?.[0] ? (
                        <div style={{ background: '#1c1a14', border: '1px solid #26231b', borderRadius: 6, padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 12, color: '#f0ebe2' }}>
                          {payload[0].name}<br />{usd(payload[0].value as number)}
                        </div>
                      ) : null
                    }
                  />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {allocationData.map((d, i) => (
                  <div key={d.name} className="flex-between" style={{ fontSize: 12 }}>
                    <div className="flex-center" style={{ gap: 6 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: PIE_COLORS[i % PIE_COLORS.length], display: 'inline-block' }} />
                      <span style={{ color: 'var(--text-2)', textTransform: 'capitalize' }}>{d.name}</span>
                    </div>
                    <span className="num" style={{ color: 'var(--text-3)', fontSize: 11 }}>
                      {pct(d.value, totalBalance)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty" style={{ padding: '32px 16px' }}>
              <div className="empty-sub">Import data to see allocation</div>
            </div>
          )}
        </div>
      </div>

      {/* Accounts + News row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20, alignItems: 'start' }}>
        {/* Accounts */}
        <div ref={accountsColRef}>
          <div className="section-label mb-16">Accounts</div>
          {accounts && accounts.length > 0 ? (
            <div className="grid-auto">
              {accounts.map((a) => (
                <div key={a.id} className="card card-hover" style={{ padding: '20px 24px' }}>
                  <div className="mb-12" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 10, alignItems: 'start' }}>
                    <span style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text)', lineHeight: 1.25, overflowWrap: 'anywhere' }}>{a.name}</span>
                    <span className={`tag tag-${a.type}`}>{a.type.replace('_', ' ')}</span>
                  </div>
                  <div className="num-mid mb-8" style={{ color: 'var(--text)' }}>
                    {usd(a.balance)}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                    {a.institution_name ?? '—'}
                    {a.last_updated && (
                      <span style={{ marginLeft: 8 }}>· {a.last_updated}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">
              <div className="empty-icon">◻</div>
              <div className="empty-title">No accounts</div>
              <div className="empty-sub">Go to Settings to add your first account, or drop a CSV into data/watch/</div>
            </div>
          )}
        </div>

        {/* News */}
        <div style={{
          height: accountsColHeight ?? undefined,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
        }}>
          <div className="section-label mb-16">Market News</div>
          {news && news.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minHeight: 0, overflowY: 'auto', paddingRight: 2 }}>
              {news.map((article, i) => {
                const hasLink = Boolean(article.url && article.url.trim())
                const cardStyle = {
                  display: 'block',
                  padding: '12px 16px',
                  background: `linear-gradient(135deg, ${NEWS_GLASS_TINTS[i % NEWS_GLASS_TINTS.length]}, rgba(12, 10, 8, 0.72))`,
                  backdropFilter: 'blur(8px)',
                  WebkitBackdropFilter: 'blur(8px)',
                  borderRadius: 8,
                  border: '1px solid var(--border-soft)',
                } as const

                if (hasLink) {
                  return (
                    <a
                      key={article.id}
                      href={article.url!}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ ...cardStyle, textDecoration: 'none', transition: 'border-color 0.15s' }}
                      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-soft)')}
                    >
                      <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
                        {article.source} · {timeAgo(article.published_at)}
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.4, fontWeight: 500, marginBottom: article.summary ? 4 : 0 }}>
                        {article.title}
                      </div>
                      {article.summary && (
                        <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.35 }}>
                          {article.summary}
                        </div>
                      )}
                    </a>
                  )
                }

                return (
                  <div key={article.id} style={cardStyle}>
                    <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
                      {article.source} · {timeAgo(article.published_at)}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.4, fontWeight: 500, marginBottom: 4 }}>
                      {article.title}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.35 }}>
                      {article.summary ?? 'Headline available. Full article may be paywalled.'}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--text-3)' }}>
                <span className="spinner" />
                <span>{newsLoading ? 'Loading market and AI news…' : 'Fetching market and AI news in background…'}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
