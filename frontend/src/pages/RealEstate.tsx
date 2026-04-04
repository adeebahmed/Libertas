import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Property, Account } from '../types'

function formatUsd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

export default function RealEstatePage() {
  const { data: properties, refetch } = useApi<Property[]>(() => api.get('/real-estate'), [])
  const { data: accounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    account_id: '',
    address: '',
    purchase_price: '',
    purchase_date: '',
    mortgage_balance: '',
    manual_override: '',
  })

  const handleSubmit = async () => {
    await api.post('/real-estate', {
      account_id: Number(form.account_id),
      address: form.address,
      purchase_price: form.purchase_price ? Number(form.purchase_price) : null,
      purchase_date: form.purchase_date || null,
      mortgage_balance: form.mortgage_balance ? Number(form.mortgage_balance) : null,
      manual_override: form.manual_override ? Number(form.manual_override) : null,
    })
    setShowForm(false)
    setForm({ account_id: '', address: '', purchase_price: '', purchase_date: '', mortgage_balance: '', manual_override: '' })
    refetch()
  }

  const handleRefresh = async (id: number) => {
    await api.post(`/real-estate/${id}/refresh-estimate`)
    refetch()
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>Real Estate</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : 'Add Property'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="form-group">
            <label>Account</label>
            <select value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })}>
              <option value="">Select account...</option>
              {accounts?.filter(a => a.type === 'real_estate').map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Address</label>
            <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="form-group">
              <label>Purchase Price</label>
              <input type="number" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Purchase Date</label>
              <input type="date" value={form.purchase_date} onChange={(e) => setForm({ ...form, purchase_date: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Mortgage Balance</label>
              <input type="number" value={form.mortgage_balance} onChange={(e) => setForm({ ...form, mortgage_balance: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Manual Value Override</label>
              <input type="number" value={form.manual_override} onChange={(e) => setForm({ ...form, manual_override: e.target.value })} />
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={!form.account_id || !form.address}>
            Add Property
          </button>
        </div>
      )}

      {properties && properties.length > 0 ? (
        <div className="card-grid">
          {properties.map((p) => (
            <div key={p.id} className="card">
              <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 12 }}>{p.address}</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 14 }}>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Current Value</div>
                  <div style={{ fontWeight: 600 }}>{p.effective_value ? formatUsd(p.effective_value) : '—'}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Mortgage</div>
                  <div style={{ fontWeight: 600 }}>{p.mortgage_balance ? formatUsd(p.mortgage_balance) : '—'}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Equity</div>
                  <div style={{ fontWeight: 600, color: 'var(--green)' }}>{formatUsd(p.equity)}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>LTV</div>
                  <div style={{ fontWeight: 600 }}>{p.ltv != null ? `${p.ltv.toFixed(1)}%` : '—'}</div>
                </div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => handleRefresh(p.id)}>
                  Refresh Estimate
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">No properties yet. Add one to track real estate equity.</div>
      )}
    </div>
  )
}
