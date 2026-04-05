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

  // Preference fields
  const [expenses, setExpenses] = useState('')
  const [risk, setRisk] = useState('moderate')
  const [claudeKey, setClaudeKey] = useState('')
  const [incomeW2, setIncomeW2] = useState('')
  const [income1099, setIncome1099] = useState('')
  const [filingStatus, setFilingStatus] = useState('single')
  const [birthYear, setBirthYear] = useState('')
  const [retirementAge, setRetirementAge] = useState('65')
  const [monthlyContribution, setMonthlyContribution] = useState('')
  const [retirementTarget, setRetirementTarget] = useState('')

  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!settings) return
    setExpenses(String(settings.monthly_expenses ?? ''))
    setRisk(String(settings.risk_profile ?? 'moderate'))
    setClaudeKey(String(settings.claude_api_key ?? ''))
    setIncomeW2(String(settings.income_w2 ?? ''))
    setIncome1099(String(settings.income_1099 ?? ''))
    setFilingStatus(String(settings.tax_filing_status ?? 'single'))
    setBirthYear(String(settings.birth_year ?? ''))
    setRetirementAge(String(settings.retirement_age ?? '65'))
    setMonthlyContribution(String(settings.monthly_contribution ?? ''))
    setRetirementTarget(String(settings.retirement_target_amount ?? ''))
  }, [settings])

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 2500) }

  const saveSetting = async (key: string, value: unknown) => {
    await api.put(`/settings/${key}`, { value })
    refetchSettings()
    showToast('Saved')
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

  const ACCOUNT_TYPES = ['brokerage', 'crypto', 'real_estate', 'savings', 'hsa', 'roth_ira', '401k', 'checking', 'credit_card', 'student_loan', 'auto_loan', 'personal_loan']

  return (
    <div>
      <h1 className="page-title">Settings</h1>

      {/* ── General ── */}
      <div className="section-label mb-16">General</div>
      <div className="card mb-32">
        <div className="grid-3">
          <div className="field">
            <label>Monthly expenses ($)</label>
            <input type="number" value={expenses} onChange={e => setExpenses(e.target.value)}
              onBlur={() => expenses !== '' && saveSetting('monthly_expenses', Number(expenses))} />
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
              onBlur={() => saveSetting('claude_api_key', claudeKey)} placeholder="sk-ant-…" />
          </div>
        </div>
      </div>

      {/* ── Income & Tax ── */}
      <div className="section-label mb-16">Income &amp; Tax</div>
      <div className="card mb-32">
        <div className="grid-3">
          <div className="field">
            <label>W-2 income ($/yr)</label>
            <input type="number" value={incomeW2} onChange={e => setIncomeW2(e.target.value)}
              onBlur={() => incomeW2 !== '' && saveSetting('income_w2', Number(incomeW2))} placeholder="e.g. 120000" />
          </div>
          <div className="field">
            <label>1099 / freelance income ($/yr)</label>
            <input type="number" value={income1099} onChange={e => setIncome1099(e.target.value)}
              onBlur={() => income1099 !== '' && saveSetting('income_1099', Number(income1099))} placeholder="e.g. 30000" />
          </div>
          <div className="field">
            <label>Filing status</label>
            <select value={filingStatus} onChange={e => { setFilingStatus(e.target.value); saveSetting('tax_filing_status', e.target.value) }}>
              <option value="single">Single</option>
              <option value="married_filing_jointly">Married Filing Jointly</option>
              <option value="married_filing_separately">Married Filing Separately</option>
              <option value="head_of_household">Head of Household</option>
            </select>
          </div>
        </div>
      </div>

      {/* ── Retirement ── */}
      <div className="section-label mb-16">Retirement</div>
      <div className="card mb-32">
        <div className="grid-4">
          <div className="field">
            <label>Birth year</label>
            <input type="number" value={birthYear} onChange={e => setBirthYear(e.target.value)}
              onBlur={() => birthYear !== '' && saveSetting('birth_year', Number(birthYear))} placeholder="e.g. 1988" />
          </div>
          <div className="field">
            <label>Target retirement age</label>
            <input type="number" value={retirementAge} onChange={e => setRetirementAge(e.target.value)}
              onBlur={() => retirementAge !== '' && saveSetting('retirement_age', Number(retirementAge))} placeholder="65" />
          </div>
          <div className="field">
            <label>Monthly contribution ($)</label>
            <input type="number" value={monthlyContribution} onChange={e => setMonthlyContribution(e.target.value)}
              onBlur={() => monthlyContribution !== '' && saveSetting('monthly_contribution', Number(monthlyContribution))} placeholder="e.g. 2000" />
          </div>
          <div className="field">
            <label>Retirement target ($, optional)</label>
            <input type="number" value={retirementTarget} onChange={e => setRetirementTarget(e.target.value)}
              onBlur={() => retirementTarget !== '' && saveSetting('retirement_target_amount', Number(retirementTarget))} placeholder="auto (25× expenses)" />
          </div>
        </div>
      </div>

      {/* ── Institutions ── */}
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

      {/* ── Accounts ── */}
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
              {ACCOUNT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
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

      {/* ── Data ── */}
      <div className="section-label mb-16">Data</div>
      <div className="flex gap-8">
        <button className="btn btn-primary" onClick={async () => { await api.post('/prices/refresh'); showToast('Prices refreshed') }}>
          Refresh prices
        </button>
        <button className="btn" onClick={async () => {
          const r = await api.post<{ id: number; filename: string }>('/backups')
          showToast(`Backup saved: ${r.filename}`)
        }}>
          Create backup
        </button>
      </div>

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
