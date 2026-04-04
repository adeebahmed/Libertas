import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, AccountDetail } from '../types'

function formatUsd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n)
}

export default function Accounts() {
  const { data: accounts, refetch } = useApi<Account[]>(() => api.get('/accounts'), [])
  const [selected, setSelected] = useState<number | null>(null)
  const { data: detail } = useApi<AccountDetail | null>(
    () => selected ? api.get(`/accounts/${selected}`) : Promise.resolve(null),
    [selected],
  )

  return (
    <div>
      <h1 className="page-title">Accounts</h1>

      {!selected ? (
        <>
          {accounts && accounts.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Institution</th>
                  <th>Balance</th>
                  <th>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => setSelected(a.id)}>
                    <td style={{ fontWeight: 600 }}>{a.name}</td>
                    <td><span className={`badge badge-${a.type}`}>{a.type.replace('_', ' ')}</span></td>
                    <td>{a.institution_name || '—'}</td>
                    <td>{formatUsd(a.balance)}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{a.last_updated || 'Never'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">No accounts. Add one in Settings.</div>
          )}
        </>
      ) : (
        <div>
          <button className="btn" onClick={() => setSelected(null)} style={{ marginBottom: 16 }}>
            Back
          </button>
          {detail && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                <h2 style={{ fontSize: 22, fontWeight: 700 }}>{detail.name}</h2>
                <span className={`badge badge-${detail.type}`}>{detail.type.replace('_', ' ')}</span>
              </div>
              <div className="stat-card" style={{ marginBottom: 20, display: 'inline-block' }}>
                <div className="label">Balance</div>
                <div className="value">{formatUsd(detail.balance)}</div>
              </div>

              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Holdings</h3>
              {detail.holdings.length > 0 ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Quantity</th>
                      <th>Cost Basis</th>
                      <th>Last Price</th>
                      <th>Market Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.holdings.map((h) => (
                      <tr key={h.id}>
                        <td style={{ fontWeight: 600 }}>{h.symbol}</td>
                        <td>{h.quantity.toFixed(4)}</td>
                        <td>{h.cost_basis != null ? formatUsd(h.cost_basis) : '—'}</td>
                        <td>{h.last_price != null ? formatUsd(h.last_price) : '—'}</td>
                        <td style={{ fontWeight: 600 }}>{formatUsd(h.market_value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty-state">No holdings. Import transactions to populate.</div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
