import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, Institution } from '../types'

export default function Settings() {
  const { data: accounts, refetch: refetchAccounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: institutions, refetch: refetchInst } = useApi<Institution[]>(() => api.get('/accounts/institutions'), [])
  const { data: settings, refetch: refetchSettings } = useApi<Record<string, unknown>>(() => api.get('/settings'), [])

  const [newAcct, setNewAcct] = useState({ name: '', type: 'brokerage', institution_id: '' })
  const [newInst, setNewInst] = useState({ name: '', export_url: '', file_pattern: '' })
  const [expenses, setExpenses] = useState('')
  const [risk, setRisk] = useState('moderate')
  const [claudeKey, setClaudeKey] = useState('')
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (settings) {
      setExpenses(String(settings.monthly_expenses ?? ''))
      setRisk(String(settings.risk_profile ?? 'moderate'))
      setClaudeKey(String(settings.claude_api_key ?? ''))
    }
  }, [settings])

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 2500) }

  const saveSetting = async (key: string, value: unknown) => {
    await api.put(`/settings/${key}`, { value })
    refetchSettings()
  }

  const addAccount = async () => {
    if (!newAcct.name) return
    await api.post('/accounts', { name: newAcct.name, type: newAcct.type, institution_id: newAcct.institution_id ? Number(newAcct.institution_id) : null })
    setNewAcct({ name: '', type: 'brokerage', institution_id: '' })
    refetchAccounts()
    showToast('Account added')
  }

  const addInstitution = async () => {
    if (!newInst.name) return
    await api.post('/accounts/institutions', { name: newInst.name, export_url: newInst.export_url || null, file_pattern: newInst.file_pattern || null })
    setNewInst({ name: '', export_url: '', file_pattern: '' })
    refetchInst()
    showToast('Institution added')
  }

  const ACCOUNT_TYPES = ['brokerage', 'crypto', 'real_estate', 'savings', 'hsa', 'roth_ira', '401k', 'checking']

  return (
    <div>
      <h1 className="page-title">Settings</h1>

      {/* Preferences */}
      <div className="section-label mb-16">Preferences</div>
      <div className="card mb-32">
        <div className="grid-3">
          <div className="field">
            <label>Monthly expenses ($)</label>
            <input type="number" value={expenses} onChange={e => setExpenses(e.target.value)}
              onBlur={() => expenses && saveSetting('monthly_expenses', Number(expenses))} />
          </div>
          <div className="field">
            <label>Risk profile</label>
            <select value={risk} onChange={e => { setRisk(e.target.value); saveSetting('risk_profile', e.target.value) }}>
              <option value="conservative">Conservative</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
          <div className="field">
            <label>Claude API key (optional)</label>
            <input type="password" value={claudeKey} onChange={e => setClaudeKey(e.target.value)}
              onBlur={() => claudeKey && saveSetting('claude_api_key', claudeKey)} placeholder="sk-ant-…" />
          </div>
        </div>
      </div>

      {/* Institutions */}
      <div className="section-label mb-16">Institutions</div>
      <div className="card mb-32" style={{ padding: 0 }}>
        {institutions && institutions.length > 0 && (
          <table className="tbl">
            <thead>
              <tr><th>Name</th><th>File Pattern</th><th>Export URL</th><th></th></tr>
            </thead>
            <tbody>
              {institutions.map(i => (
                <tr key={i.id}>
                  <td style={{ fontWeight: 500 }}>{i.name}</td>
                  <td className="num" style={{ fontSize: 12, color: 'var(--text-3)' }}>{i.file_pattern ?? '—'}</td>
                  <td>{i.export_url ? <a href={i.export_url} target="_blank" rel="noopener">↗ Open</a> : '—'}</td>
                  <td><button className="btn btn-sm" onClick={async () => { await api.delete(`/accounts/institutions/${i.id}`); refetchInst() }}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ padding: '16px 20px', borderTop: institutions?.length ? '1px solid var(--border-soft)' : 'none', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 12, alignItems: 'end' }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Name</label>
            <input value={newInst.name} onChange={e => setNewInst(p => ({ ...p, name: e.target.value }))} placeholder="e.g. Fidelity" />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Export URL</label>
            <input value={newInst.export_url} onChange={e => setNewInst(p => ({ ...p, export_url: e.target.value }))} placeholder="https://…" />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>File pattern</label>
            <input value={newInst.file_pattern} onChange={e => setNewInst(p => ({ ...p, file_pattern: e.target.value }))} placeholder="Fidelity_*.csv" />
          </div>
          <button className="btn btn-primary" onClick={addInstitution} disabled={!newInst.name}>Add</button>
        </div>
      </div>

      {/* Accounts */}
      <div className="section-label mb-16">Accounts</div>
      <div className="card mb-32" style={{ padding: 0 }}>
        {accounts && accounts.length > 0 && (
          <table className="tbl">
            <thead>
              <tr><th>Name</th><th>Type</th><th>Institution</th><th></th></tr>
            </thead>
            <tbody>
              {accounts.map(a => (
                <tr key={a.id}>
                  <td style={{ fontWeight: 500 }}>{a.name}</td>
                  <td><span className={`tag tag-${a.type}`}>{a.type.replace('_', ' ')}</span></td>
                  <td style={{ color: 'var(--text-2)' }}>{a.institution_name ?? '—'}</td>
                  <td><button className="btn btn-sm" onClick={async () => { await api.delete(`/accounts/${a.id}`); refetchAccounts() }}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ padding: '16px 20px', borderTop: accounts?.length ? '1px solid var(--border-soft)' : 'none', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 12, alignItems: 'end' }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Name</label>
            <input value={newAcct.name} onChange={e => setNewAcct(p => ({ ...p, name: e.target.value }))} placeholder="e.g. Fidelity Roth IRA" />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Type</label>
            <select value={newAcct.type} onChange={e => setNewAcct(p => ({ ...p, type: e.target.value }))}>
              {ACCOUNT_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Institution</label>
            <select value={newAcct.institution_id} onChange={e => setNewAcct(p => ({ ...p, institution_id: e.target.value }))}>
              <option value="">None</option>
              {institutions?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" onClick={addAccount} disabled={!newAcct.name}>Add</button>
        </div>
      </div>

      {/* Data actions */}
      <div className="section-label mb-16">Data</div>
      <div className="flex gap-8">
        <button className="btn btn-primary" onClick={async () => { await api.post('/prices/refresh'); showToast('Prices refreshed') }}>
          Refresh prices
        </button>
        <button className="btn" onClick={async () => {
          const data = { accounts, institutions, settings }
          const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          Object.assign(document.createElement('a'), { href: url, download: `libertas-${new Date().toISOString().split('T')[0]}.json` }).click()
          URL.revokeObjectURL(url)
        }}>
          Export backup
        </button>
      </div>

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
