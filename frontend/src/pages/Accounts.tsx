import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, AccountDetail } from '../types'
import { IconChevronLeft } from '../components/Icons'

function usd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n)
}

function Sparkline({ value, cost }: { value: number; cost: number | null }) {
  if (!cost || cost === 0) return null
  const gain = ((value - cost) / cost) * 100
  const up = gain >= 0
  return (
    <span className={up ? 'delta-up' : 'delta-down'} style={{ marginLeft: 8 }}>
      {up ? '↑' : '↓'}{Math.abs(gain).toFixed(1)}%
    </span>
  )
}

export default function Accounts() {
  const { data: accounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const [selected, setSelected] = useState<number | null>(null)
  const { data: detail } = useApi<AccountDetail | null>(
    () => selected ? api.get(`/accounts/${selected}`) : Promise.resolve(null),
    [selected],
  )

  if (selected && detail) {
    return (
      <div>
        <button className="back-link" onClick={() => setSelected(null)}>
          <IconChevronLeft size={14} />
          Accounts
        </button>

        <div className="flex-between mb-32" style={{ paddingBottom: 24, borderBottom: '1px solid var(--border)' }}>
          <div>
            <div className="section-label mb-8">{detail.institution_name ?? 'Account'}</div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 28, fontWeight: 500 }}>{detail.name}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="section-label mb-8">Balance</div>
            <div className="num-large">{usd(detail.balance)}</div>
          </div>
        </div>

        {detail.holdings.length > 0 ? (
          <div className="card" style={{ padding: 0 }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Shares</th>
                  <th>Avg Cost</th>
                  <th>Last Price</th>
                  <th style={{ textAlign: 'right' }}>Market Value</th>
                  <th style={{ textAlign: 'right' }}>Return</th>
                </tr>
              </thead>
              <tbody>
                {detail.holdings
                  .sort((a, b) => b.market_value - a.market_value)
                  .map((h) => {
                    const avgCost = h.cost_basis && h.quantity ? h.cost_basis / h.quantity : null
                    const gain = h.last_price && avgCost ? h.last_price - avgCost : null
                    const gainPct = gain && avgCost && avgCost !== 0 ? (gain / avgCost) * 100 : null
                    return (
                      <tr key={h.id}>
                        <td style={{ fontWeight: 500, letterSpacing: 0.3 }}>{h.symbol}</td>
                        <td className="num" style={{ color: 'var(--text-2)' }}>{h.quantity.toFixed(4)}</td>
                        <td className="num" style={{ color: 'var(--text-2)' }}>{avgCost ? usd(avgCost) : '—'}</td>
                        <td className="num" style={{ color: 'var(--text-2)' }}>{h.last_price ? usd(h.last_price) : '—'}</td>
                        <td className="num" style={{ textAlign: 'right', fontWeight: 500 }}>{usd(h.market_value)}</td>
                        <td style={{ textAlign: 'right' }}>
                          {gainPct != null ? (
                            <span className={gainPct >= 0 ? 'delta-up' : 'delta-down'}>
                              {gainPct >= 0 ? '+' : ''}{gainPct.toFixed(1)}%
                            </span>
                          ) : '—'}
                        </td>
                      </tr>
                    )
                  })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">
            <div className="empty-title">No holdings</div>
            <div className="empty-sub">Import transactions to populate this account</div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <h1 className="page-title">Accounts</h1>

      {accounts && accounts.length > 0 ? (
        <div className="card" style={{ padding: 0 }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Institution</th>
                <th style={{ textAlign: 'right' }}>Balance</th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {accounts
                .sort((a, b) => b.balance - a.balance)
                .map((a) => (
                  <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => setSelected(a.id)}>
                    <td style={{ fontWeight: 500 }}>{a.name}</td>
                    <td><span className={`tag tag-${a.type}`}>{a.type.replace('_', ' ')}</span></td>
                    <td style={{ color: 'var(--text-2)' }}>{a.institution_name ?? '—'}</td>
                    <td className="num" style={{ textAlign: 'right', fontWeight: 500 }}>{usd(a.balance)}</td>
                    <td className="num" style={{ color: 'var(--text-3)', fontSize: 12 }}>{a.last_updated ?? '—'}</td>
                  </tr>
                ))}
              <tr style={{ background: 'var(--bg-elevated)' }}>
                <td colSpan={3} style={{ fontWeight: 500, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.6px', color: 'var(--text-3)' }}>Total</td>
                <td className="num" style={{ textAlign: 'right', fontWeight: 500 }}>
                  {usd(accounts.reduce((s, a) => s + a.balance, 0))}
                </td>
                <td />
              </tr>
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">
          <div className="empty-icon">◻</div>
          <div className="empty-title">No accounts yet</div>
          <div className="empty-sub">Add accounts in Settings or import a CSV file</div>
        </div>
      )}
    </div>
  )
}
