import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, Institution } from '../types'

export default function Settings() {
  const { data: accounts, refetch: refetchAccounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: institutions, refetch: refetchInst } = useApi<Institution[]>(() => api.get('/accounts/institutions'), [])
  const { data: settings, refetch: refetchSettings } = useApi<Record<string, unknown>>(() => api.get('/settings'), [])

  // Add account form
  const [newAccount, setNewAccount] = useState({ name: '', type: 'brokerage', institution_id: '' })
  // Add institution form
  const [newInst, setNewInst] = useState({ name: '', export_url: '', file_pattern: '', importer_preset: 'generic', notes: '' })
  // Settings
  const [expenses, setExpenses] = useState('')
  const [riskProfile, setRiskProfile] = useState('moderate')
  const [claudeKey, setClaudeKey] = useState('')

  useEffect(() => {
    if (settings) {
      setExpenses(String(settings.monthly_expenses ?? ''))
      setRiskProfile(String(settings.risk_profile ?? 'moderate'))
      setClaudeKey(String(settings.claude_api_key ?? ''))
    }
  }, [settings])

  const handleAddAccount = async () => {
    await api.post('/accounts', {
      name: newAccount.name,
      type: newAccount.type,
      institution_id: newAccount.institution_id ? Number(newAccount.institution_id) : null,
    })
    setNewAccount({ name: '', type: 'brokerage', institution_id: '' })
    refetchAccounts()
  }

  const handleAddInstitution = async () => {
    await api.post('/accounts/institutions', {
      name: newInst.name,
      export_url: newInst.export_url || null,
      file_pattern: newInst.file_pattern || null,
      importer_preset: newInst.importer_preset,
      notes: newInst.notes || null,
    })
    setNewInst({ name: '', export_url: '', file_pattern: '', importer_preset: 'generic', notes: '' })
    refetchInst()
  }

  const handleDeleteAccount = async (id: number) => {
    await api.delete(`/accounts/${id}`)
    refetchAccounts()
  }

  const handleDeleteInstitution = async (id: number) => {
    await api.delete(`/accounts/institutions/${id}`)
    refetchInst()
  }

  const saveSetting = async (key: string, value: unknown) => {
    await api.put(`/settings/${key}`, { value })
    refetchSettings()
  }

  const handleRefreshPrices = async () => {
    await api.post('/prices/refresh')
    alert('Prices refreshed!')
  }

  const handleExportData = async () => {
    const data = {
      accounts: accounts,
      institutions: institutions,
      settings: settings,
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `libertas-backup-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const ACCOUNT_TYPES = ['brokerage', 'crypto', 'real_estate', 'savings', 'hsa', 'roth_ira', '401k', 'checking']
  const PRESETS = ['generic', 'fidelity', 'schwab', 'coinbase', 'robinhood']

  return (
    <div>
      <h1 className="page-title">Settings</h1>

      {/* Institutions */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Institutions</h3>
        {institutions && institutions.length > 0 && (
          <table className="table" style={{ marginBottom: 16 }}>
            <thead>
              <tr><th>Name</th><th>Preset</th><th>File Pattern</th><th>Export URL</th><th></th></tr>
            </thead>
            <tbody>
              {institutions.map((i) => (
                <tr key={i.id}>
                  <td style={{ fontWeight: 600 }}>{i.name}</td>
                  <td><span className="badge badge-brokerage">{i.importer_preset}</span></td>
                  <td style={{ color: 'var(--text-secondary)' }}>{i.file_pattern || '—'}</td>
                  <td>{i.export_url ? <a href={i.export_url} target="_blank" rel="noopener">Open</a> : '—'}</td>
                  <td><button className="btn" style={{ fontSize: 12, padding: '2px 8px' }} onClick={() => handleDeleteInstitution(i.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr auto', gap: 8, alignItems: 'end' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Name</label>
            <input value={newInst.name} onChange={(e) => setNewInst({ ...newInst, name: e.target.value })} placeholder="e.g. Fidelity" />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Export URL</label>
            <input value={newInst.export_url} onChange={(e) => setNewInst({ ...newInst, export_url: e.target.value })} placeholder="https://..." />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>File Pattern</label>
            <input value={newInst.file_pattern} onChange={(e) => setNewInst({ ...newInst, file_pattern: e.target.value })} placeholder="Fidelity_*.csv" />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Preset</label>
            <select value={newInst.importer_preset} onChange={(e) => setNewInst({ ...newInst, importer_preset: e.target.value })}>
              {PRESETS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleAddInstitution} disabled={!newInst.name}>Add</button>
        </div>
      </div>

      {/* Accounts */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Accounts</h3>
        {accounts && accounts.length > 0 && (
          <table className="table" style={{ marginBottom: 16 }}>
            <thead>
              <tr><th>Name</th><th>Type</th><th>Institution</th><th></th></tr>
            </thead>
            <tbody>
              {accounts.map((a) => (
                <tr key={a.id}>
                  <td style={{ fontWeight: 600 }}>{a.name}</td>
                  <td><span className={`badge badge-${a.type}`}>{a.type.replace('_', ' ')}</span></td>
                  <td>{a.institution_name || '—'}</td>
                  <td><button className="btn" style={{ fontSize: 12, padding: '2px 8px' }} onClick={() => handleDeleteAccount(a.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 8, alignItems: 'end' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Name</label>
            <input value={newAccount.name} onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })} placeholder="e.g. Fidelity Roth IRA" />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Type</label>
            <select value={newAccount.type} onChange={(e) => setNewAccount({ ...newAccount, type: e.target.value })}>
              {ACCOUNT_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Institution</label>
            <select value={newAccount.institution_id} onChange={(e) => setNewAccount({ ...newAccount, institution_id: e.target.value })}>
              <option value="">None</option>
              {institutions?.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleAddAccount} disabled={!newAccount.name}>Add</button>
        </div>
      </div>

      {/* App Settings */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Preferences</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
          <div className="form-group">
            <label>Monthly Expenses ($)</label>
            <input type="number" value={expenses} onChange={(e) => setExpenses(e.target.value)}
              onBlur={() => saveSetting('monthly_expenses', Number(expenses))} />
          </div>
          <div className="form-group">
            <label>Risk Profile</label>
            <select value={riskProfile} onChange={(e) => { setRiskProfile(e.target.value); saveSetting('risk_profile', e.target.value) }}>
              <option value="conservative">Conservative</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
          <div className="form-group">
            <label>Claude API Key (optional)</label>
            <input type="password" value={claudeKey} onChange={(e) => setClaudeKey(e.target.value)}
              onBlur={() => claudeKey && saveSetting('claude_api_key', claudeKey)} placeholder="sk-ant-..." />
          </div>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 12 }}>
        <button className="btn btn-primary" onClick={handleRefreshPrices}>Refresh All Prices</button>
        <button className="btn" onClick={handleExportData}>Export Data as JSON</button>
      </div>
    </div>
  )
}
