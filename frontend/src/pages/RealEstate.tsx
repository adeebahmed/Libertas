import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Property } from '../types'

function usd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function LTVPill({ ltv }: { ltv: number }) {
  const color = ltv > 80 ? 'var(--neg)' : ltv > 60 ? 'var(--accent)' : 'var(--pos)'
  return (
    <span className="num" style={{ color, fontSize: 'var(--fs-xs)' }}>
      {ltv.toFixed(1)}%
    </span>
  )
}

export default function RealEstatePage() {
  const { data: properties, loading, error, refetch } = useApi<Property[]>(() => api.get('/real-estate'), [])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    address: '',
    purchase_price: '',
    purchase_date: '',
    mortgage_balance: '',
    mortgage_rate: '',
    manual_override: '',
  })

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((p) => ({ ...p, [k]: e.target.value }))

  const handleAdd = async () => {
    await api.post('/real-estate', {
      address: form.address,
      purchase_price: form.purchase_price ? Number(form.purchase_price) : null,
      purchase_date: form.purchase_date || null,
      mortgage_balance: form.mortgage_balance ? Number(form.mortgage_balance) : null,
      mortgage_rate: form.mortgage_rate ? Number(form.mortgage_rate) : null,
      manual_override: form.manual_override ? Number(form.manual_override) : null,
    })
    setShowForm(false)
    setForm({ address: '', purchase_price: '', purchase_date: '', mortgage_balance: '', mortgage_rate: '', manual_override: '' })
    refetch()
  }

  const totalEquity = properties?.reduce((s, p) => s + p.equity, 0) ?? 0
  const totalValue = properties?.reduce((s, p) => s + (p.effective_value ?? 0), 0) ?? 0

  return (
    <div>
      <div className="flex-between mb-32">
        <div>
          <h1 className="page-title" style={{ marginBottom: 4 }}>Real Estate</h1>
          {properties && properties.length > 0 && (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-sm)', color: 'var(--text-3)' }}>
              {properties.length} {properties.length === 1 ? 'property' : 'properties'}
              {' · '}
              <span style={{ color: 'var(--text-2)' }}>{usd(totalValue)} value</span>
              {' · '}
              <span style={{ color: 'var(--pos)' }}>{usd(totalEquity)} equity</span>
            </div>
          )}
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : 'Add Property'}
        </button>
      </div>

      {showForm && (
        <div className="card mb-24">
          <div className="section-label mb-16">New Property</div>
          <div className="grid-2">
            <div className="field">
              <label>Address</label>
              <input value={form.address} onChange={f('address')} placeholder="123 Main St, City, ST" />
            </div>
            <div className="field">
              <label>Purchase price</label>
              <input type="number" value={form.purchase_price} onChange={f('purchase_price')} />
            </div>
            <div className="field">
              <label>Purchase date</label>
              <input type="date" value={form.purchase_date} onChange={f('purchase_date')} />
            </div>
            <div className="field">
              <label>Mortgage balance</label>
              <input type="number" value={form.mortgage_balance} onChange={f('mortgage_balance')} />
            </div>
            <div className="field">
              <label>Mortgage rate (%)</label>
              <input type="number" step="0.01" value={form.mortgage_rate} onChange={f('mortgage_rate')} placeholder="6.75" />
            </div>
            <div className="field">
              <label>Manual value override</label>
              <input type="number" value={form.manual_override} onChange={f('manual_override')} placeholder="Leave blank to use Zillow" />
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleAdd} disabled={!form.address}>
            Add Property
          </button>
        </div>
      )}

      {error ? (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-sm)', color: 'var(--neg)', padding: '12px 0', borderTop: '1px solid var(--neg)' }}>
          ERR · Failed to load properties
        </div>
      ) : loading && !properties ? (
        <div className="empty">
          <span className="spinner" aria-label="Loading properties" />
          <div className="empty-sub" style={{ marginTop: 10 }}>Loading properties…</div>
        </div>
      ) : properties && properties.length > 0 ? (
        <div className="card" style={{ padding: 0 }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Address</th>
                <th style={{ textAlign: 'right' }}>Value</th>
                <th style={{ textAlign: 'right' }}>Mortgage</th>
                <th style={{ textAlign: 'right' }}>Rate</th>
                <th style={{ textAlign: 'right' }}>LTV</th>
                <th style={{ textAlign: 'right' }}>Equity</th>
                <th style={{ textAlign: 'right' }}>Purchased</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {properties.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontWeight: 500, maxWidth: 280 }}>{p.address}</td>
                  <td className="num" style={{ textAlign: 'right' }}>{p.effective_value ? usd(p.effective_value) : '—'}</td>
                  <td className="num" style={{ textAlign: 'right' }}>{p.mortgage_balance ? usd(p.mortgage_balance) : '—'}</td>
                  <td className="num" style={{ textAlign: 'right', color: 'var(--text-2)' }}>
                    {p.mortgage_rate != null ? `${p.mortgage_rate.toFixed(2)}%` : '—'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {p.ltv != null ? <LTVPill ltv={p.ltv} /> : <span style={{ color: 'var(--text-3)' }}>—</span>}
                  </td>
                  <td className="num" style={{ textAlign: 'right', color: 'var(--pos)', fontWeight: 500 }}>{usd(p.equity)}</td>
                  <td className="num" style={{ textAlign: 'right', color: 'var(--text-3)' }}>
                    {p.purchase_price ? usd(p.purchase_price) : '—'}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm"
                      onClick={async () => {
                        await api.post(`/real-estate/${p.id}/refresh-estimate`)
                        refetch()
                      }}
                    >
                      Refresh
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !showForm ? (
        <div className="empty">
          <div className="empty-title">No properties</div>
          <div className="empty-sub">Add a property to track equity and LTV.</div>
          <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => setShowForm(true)}>
            Add Property
          </button>
        </div>
      ) : null}
    </div>
  )
}
