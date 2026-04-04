import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Property, Account } from '../types'

function usd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function LTVBar({ ltv }: { ltv: number }) {
  const clamped = Math.min(ltv, 100)
  const color = ltv > 80 ? 'var(--red)' : ltv > 60 ? 'var(--gold)' : 'var(--green)'
  return (
    <div style={{ marginTop: 12 }}>
      <div className="flex-between mb-8" style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
        <span>LTV</span><span>{ltv.toFixed(1)}%</span>
      </div>
      <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${clamped}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.4s' }} />
      </div>
    </div>
  )
}

export default function RealEstatePage() {
  const { data: properties, refetch } = useApi<Property[]>(() => api.get('/real-estate'), [])
  const { data: accounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ account_id: '', address: '', purchase_price: '', purchase_date: '', mortgage_balance: '', manual_override: '' })

  const reAccounts = accounts?.filter(a => a.type === 'real_estate') ?? []
  const f = (k: string) => (e: any) => setForm(p => ({ ...p, [k]: e.target.value }))

  const handleAdd = async () => {
    await api.post('/real-estate', {
      account_id: Number(form.account_id),
      address: form.address,
      purchase_price: form.purchase_price ? Number(form.purchase_price) : null,
      purchase_date: form.purchase_date || null,
      mortgage_balance: form.mortgage_balance ? Number(form.mortgage_balance) : null,
      manual_override: form.manual_override ? Number(form.manual_override) : null,
    })
    setShowForm(false)
    refetch()
  }

  const totalEquity = properties?.reduce((s, p) => s + p.equity, 0) ?? 0

  return (
    <div>
      <div className="flex-between mb-32">
        <div>
          <h1 className="page-title" style={{ marginBottom: 4 }}>Real Estate</h1>
          {properties && properties.length > 0 && (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-2)' }}>
              {properties.length} {properties.length === 1 ? 'property' : 'properties'} · {usd(totalEquity)} equity
            </div>
          )}
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ Add Property'}
        </button>
      </div>

      {showForm && (
        <div className="card mb-24">
          <div className="grid-2">
            <div className="field">
              <label>Account</label>
              <select value={form.account_id} onChange={f('account_id')}>
                <option value="">Select account…</option>
                {reAccounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Address</label>
              <input value={form.address} onChange={f('address')} placeholder="123 Main St, City, ST" />
            </div>
            <div className="field">
              <label>Purchase Price</label>
              <input type="number" value={form.purchase_price} onChange={f('purchase_price')} />
            </div>
            <div className="field">
              <label>Purchase Date</label>
              <input type="date" value={form.purchase_date} onChange={f('purchase_date')} />
            </div>
            <div className="field">
              <label>Mortgage Balance</label>
              <input type="number" value={form.mortgage_balance} onChange={f('mortgage_balance')} />
            </div>
            <div className="field">
              <label>Manual Value Override</label>
              <input type="number" value={form.manual_override} onChange={f('manual_override')} placeholder="Leave blank to use Zillow" />
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleAdd} disabled={!form.account_id || !form.address}>
            Add Property
          </button>
        </div>
      )}

      {properties && properties.length > 0 ? (
        <div className="grid-auto">
          {properties.map(p => (
            <div key={p.id} className="card">
              <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 16, lineHeight: 1.4 }}>{p.address}</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 0', fontSize: 13 }}>
                <div>
                  <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 2 }}>Value</div>
                  <div className="num" style={{ fontWeight: 500 }}>{p.effective_value ? usd(p.effective_value) : '—'}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 2 }}>Mortgage</div>
                  <div className="num" style={{ fontWeight: 500 }}>{p.mortgage_balance ? usd(p.mortgage_balance) : '—'}</div>
                </div>
                <div style={{ marginTop: 8 }}>
                  <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 2 }}>Equity</div>
                  <div className="num" style={{ color: 'var(--green)', fontWeight: 500 }}>{usd(p.equity)}</div>
                </div>
                <div style={{ marginTop: 8 }}>
                  <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 2 }}>Purchased</div>
                  <div className="num" style={{ fontSize: 13 }}>{p.purchase_price ? usd(p.purchase_price) : '—'}</div>
                </div>
              </div>
              {p.ltv != null && <LTVBar ltv={p.ltv} />}
              <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
                <button className="btn btn-sm" onClick={async () => { await api.post(`/real-estate/${p.id}/refresh-estimate`); refetch() }}>
                  Refresh estimate
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : !showForm && (
        <div className="empty">
          <div className="empty-icon">⌂</div>
          <div className="empty-title">No properties</div>
          <div className="empty-sub">Add a property to track equity and LTV</div>
        </div>
      )}
    </div>
  )
}
