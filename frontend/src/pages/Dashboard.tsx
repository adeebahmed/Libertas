import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { NetWorth, BalanceSnapshot, Account } from '../types'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'

const COLORS = ['#6366f1', '#f59e0b', '#22c55e', '#06b6d4', '#a855f7', '#ec4899', '#14b8a6', '#64748b']

function formatUsd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function staleness(dateStr: string | null): string {
  if (!dateStr) return 'staleness-red'
  const days = (Date.now() - new Date(dateStr).getTime()) / 86400000
  if (days < 3) return 'staleness-green'
  if (days < 7) return 'staleness-yellow'
  return 'staleness-red'
}

export default function Dashboard() {
  const { data: nw } = useApi<NetWorth>(() => api.get('/snapshots/current'), [])
  const { data: history } = useApi<BalanceSnapshot[]>(() => api.get('/snapshots/net-worth'), [])
  const { data: accounts } = useApi<Account[]>(() => api.get('/accounts'), [])

  const allocationData = nw
    ? Object.entries(nw.by_type).map(([name, value]) => ({ name, value }))
    : []

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">Net Worth</div>
          <div className="value">{nw ? formatUsd(nw.net_worth) : '$--'}</div>
          {nw && (
            <div className={`delta ${nw.delta >= 0 ? 'positive' : 'negative'}`}>
              {nw.delta >= 0 ? '+' : ''}{formatUsd(nw.delta)}
            </div>
          )}
        </div>
        <div className="stat-card">
          <div className="label">Accounts</div>
          <div className="value">{accounts?.length ?? '--'}</div>
        </div>
        <div className="stat-card">
          <div className="label">Asset Classes</div>
          <div className="value">{allocationData.length || '--'}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginBottom: 24 }}>
        <div className="card">
          <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>Net Worth Over Time</h3>
          {history && history.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={history}>
                <XAxis dataKey="date" tick={{ fill: '#8888a0', fontSize: 12 }} />
                <YAxis tick={{ fill: '#8888a0', fontSize: 12 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ background: '#1a1a26', border: '1px solid #1f1f2e', borderRadius: 8 }}
                  formatter={(v: number) => [formatUsd(v), 'Net Worth']}
                />
                <Line type="monotone" dataKey="net_worth" stroke="#6366f1" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">Import data to see your net worth trend</div>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>Asset Allocation</h3>
          {allocationData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={allocationData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                  nameKey="name"
                >
                  {allocationData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1a1a26', border: '1px solid #1f1f2e', borderRadius: 8 }}
                  formatter={(v: number) => [formatUsd(v)]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">No allocation data yet</div>
          )}
        </div>
      </div>

      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Accounts</h3>
      {accounts && accounts.length > 0 ? (
        <div className="card-grid">
          {accounts.map((a) => (
            <div key={a.id} className="card" style={{ cursor: 'pointer' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>{a.name}</span>
                <span className={`badge badge-${a.type}`}>{a.type.replace('_', ' ')}</span>
              </div>
              <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.5 }}>{formatUsd(a.balance)}</div>
              {a.institution_name && (
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{a.institution_name}</div>
              )}
              <div style={{ fontSize: 12, marginTop: 8 }}>
                <span className={staleness(a.last_updated)}>
                  {a.last_updated ? `Updated ${a.last_updated}` : 'No data yet'}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">No accounts yet. Go to Settings to add one.</div>
      )}
    </div>
  )
}
