import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, Institution, IntegrationConnection } from '../types'
import Confirm from '../components/Confirm'
import { useTheme, type Theme } from '../theme'

type SeedDemoResponse = {
  ok: boolean
  rows_imported: number
  rows_skipped: number
  errors: { file: string; error: string }[]
}

export default function Settings() {
  const { data: accounts, refetch: refetchAccounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: institutions, refetch: refetchInst } = useApi<Institution[]>(() => api.get('/accounts/institutions'), [])
  const { data: settings, refetch: refetchSettings } = useApi<Record<string, unknown>>(() => api.get('/settings'), [])
  const { data: integrationStatus, refetch: refetchIntegrations } = useApi<{ connections: IntegrationConnection[] }>(
    () => api.get('/integrations/status'),
    [],
  )

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

  const [confirmPending, setConfirmPending] = useState<{ message: string; detail?: string; onConfirm: () => void } | null>(null)
  const [toast, setToast] = useState('')
  const [plaidLinkToken, setPlaidLinkToken] = useState('')
  const [plaidPublicToken, setPlaidPublicToken] = useState('')
  const [plaidConnectionName, setPlaidConnectionName] = useState('')
  const [sheetsName, setSheetsName] = useState('')
  const [sheetsCsvUrl, setSheetsCsvUrl] = useState('')
  const [sheetsAccountId, setSheetsAccountId] = useState('')
  const [sheetsValidation, setSheetsValidation] = useState('')
  const [sheetsMappingPreset, setSheetsMappingPreset] = useState('default')
  const [busyAction, setBusyAction] = useState<string | null>(null)

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
  const actionError = (e: any) => e?.message || 'Request failed'

  const runAction = async (key: string, fn: () => Promise<void>) => {
    if (busyAction) return
    try {
      setBusyAction(key)
      await fn()
    } catch (e: any) {
      showToast(actionError(e))
    } finally {
      setBusyAction(null)
    }
  }

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

  const removeInstitution = (institution: Institution) => {
    setConfirmPending({
      message: `Remove ${institution.name}?`,
      detail: 'Accounts using this institution may lose their institution link.',
      onConfirm: async () => {
        setConfirmPending(null)
        await api.delete('/accounts/institutions/' + institution.id)
        refetchInst()
        showToast('Institution removed')
      },
    })
  }

  const removeAccount = (account: Account) => {
    setConfirmPending({
      message: `Remove ${account.name}?`,
      detail: 'This deletes the account, holdings, balance history, and transactions. This cannot be undone.',
      onConfirm: async () => {
        setConfirmPending(null)
        await api.delete('/accounts/' + account.id)
        refetchAccounts()
        showToast('Account removed')
      },
    })
  }

  const seedDemoData = async () => {
    const result = await api.post<SeedDemoResponse>('/settings/seed-demo')
    refetchAccounts()
    refetchInst()

    if (result.errors?.length) {
      showToast(`Demo load finished with ${result.errors.length} file error(s)`)
      return
    }
    if (result.rows_imported > 0) {
      showToast(`Loaded fake demo data (${result.rows_imported} rows imported)`)
      return
    }
    showToast('Fake demo data already loaded')
  }

  const createPlaidLinkToken = async () => {
    const result = await api.post<{ link_token: string }>('/integrations/plaid/create-link-token', { user_id: 'local-user' })
    setPlaidLinkToken(result.link_token || '')
    showToast('Plaid link token created')
  }

  const exchangePlaidPublicToken = async () => {
    if (!plaidPublicToken.trim()) return
    await api.post('/integrations/plaid/exchange-public-token', {
      public_token: plaidPublicToken.trim(),
      name: plaidConnectionName.trim() || null,
    })
    setPlaidPublicToken('')
    setPlaidConnectionName('')
    refetchIntegrations()
    showToast('Plaid connection saved')
  }

  const syncPlaid = async (connectionId?: number) => {
    await api.post('/integrations/plaid/sync-now', connectionId ? { connection_id: connectionId } : {})
    refetchIntegrations()
    refetchAccounts()
    showToast('Plaid sync complete')
  }

  const setPlaidRelink = async (connectionId: number) => {
    await api.post('/integrations/plaid/relink', { connection_id: connectionId })
    refetchIntegrations()
    showToast('Relink requested')
  }

  const disconnectPlaid = async (connectionId: number) => {
    await api.post('/integrations/plaid/disconnect', { connection_id: connectionId })
    refetchIntegrations()
    showToast('Plaid disconnected')
  }

  const validateSheetsFeed = async () => {
    if (!sheetsCsvUrl.trim()) return
    const result = await api.post<{ row_count: number; headers: string[] }>('/integrations/sheets/validate-feed', { csv_url: sheetsCsvUrl.trim() })
    setSheetsValidation(`Valid feed · ${result.row_count} rows · headers: ${result.headers.join(', ')}`)
    showToast('Sheets feed validated')
  }

  const addSheetsFeed = async () => {
    if (!sheetsName.trim() || !sheetsCsvUrl.trim() || !sheetsAccountId) return
    const mappingPresets: Record<string, Record<string, string>> = {
      default: {},
      bank_statement: {
        date: 'Date',
        amount: 'Amount',
        description: 'Description',
        type: 'Type',
        row_id: 'Transaction ID',
      },
      brokerage_export: {
        date: 'Trade Date',
        amount: 'Net Amount',
        description: 'Description',
        type: 'Action',
        symbol: 'Symbol',
        quantity: 'Quantity',
        price: 'Price',
        row_id: 'Activity ID',
      },
    }
    await api.post('/integrations/sheets/add-feed', {
      name: sheetsName.trim(),
      csv_url: sheetsCsvUrl.trim(),
      account_id: Number(sheetsAccountId),
      mapping: mappingPresets[sheetsMappingPreset] ?? {},
    })
    setSheetsName('')
    setSheetsCsvUrl('')
    setSheetsAccountId('')
    setSheetsValidation('')
    setSheetsMappingPreset('default')
    refetchIntegrations()
    showToast('Sheets feed added')
  }

  const syncSheets = async (connectionId?: number) => {
    await api.post('/integrations/sheets/sync-now', connectionId ? { connection_id: connectionId } : {})
    refetchIntegrations()
    refetchAccounts()
    showToast('Sheets sync complete')
  }

  const disableSheetsFeed = async (connectionId: number) => {
    await api.post('/integrations/sheets/disable-feed', { connection_id: connectionId })
    refetchIntegrations()
    showToast('Sheets feed disabled')
  }

  const ACCOUNT_TYPES = ['brokerage', 'crypto', 'savings', 'hsa', 'roth_ira', '401k', 'checking', 'credit_card', 'student_loan', 'auto_loan', 'personal_loan']

  const { theme, setTheme } = useTheme()

  return (
    <div>
      <h1 className="page-title">Settings</h1>

      {/* ── Appearance ── */}
      <div className="section-label mb-16">Appearance</div>
      <div className="card mb-32">
        <div className="grid-3">
          <div className="field">
            <label>Theme</label>
            <select value={theme} onChange={e => setTheme(e.target.value as Theme)}>
              <option value="onyx">Onyx (dark)</option>
              <option value="retro">Retro (blue)</option>
            </select>
          </div>
        </div>
      </div>

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
                  <td className="num" style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)' }}>{i.file_pattern ?? '—'}</td>
                  <td>{i.export_url ? <a href={i.export_url} target="_blank" rel="noopener">↗ Open</a> : '—'}</td>
                  <td><button className="btn btn-sm" onClick={() => removeInstitution(i)}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="settings-inline-form" style={{ padding: '16px 20px', borderTop: institutions?.length ? '1px solid var(--border)' : 'none', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 12, alignItems: 'end' }}>
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
                  <td><button className="btn btn-sm" onClick={() => removeAccount(a)}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="settings-inline-form" style={{ padding: '16px 20px', borderTop: accounts?.length ? '1px solid var(--border)' : 'none', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 12, alignItems: 'end' }}>
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

      {/* ── Integrations ── */}
      <div className="section-label mb-16">Integrations</div>
      <div className="card mb-32">
        <div style={{ marginBottom: 16, color: 'var(--text-2)', fontSize: 'var(--fs-base)' }}>
          Optional only. CSV/Excel/manual workflows continue to work exactly the same if you do nothing here.
        </div>
        <div className="grid-2" style={{ gap: 16 }}>
          <div className="card" style={{ padding: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 'var(--s-2)' }}>Plaid (optional)</div>
            <div className="field">
              <label>Connection name</label>
              <input value={plaidConnectionName} onChange={e => setPlaidConnectionName(e.target.value)} placeholder="e.g. Chase via Plaid" />
            </div>
            <div className="field">
              <label>Public token (from Plaid Link)</label>
              <input value={plaidPublicToken} onChange={e => setPlaidPublicToken(e.target.value)} placeholder="public-sandbox-..." />
            </div>
            <div className="flex gap-8" style={{ marginBottom: 'var(--s-2)' }}>
              <button className="btn" onClick={() => runAction('plaid-link', createPlaidLinkToken)} disabled={!!busyAction}>
                {busyAction === 'plaid-link' ? 'Working…' : 'Create link token'}
              </button>
              <button
                className="btn btn-primary"
                onClick={() => runAction('plaid-exchange', exchangePlaidPublicToken)}
                disabled={!plaidPublicToken.trim() || !!busyAction}
              >
                {busyAction === 'plaid-exchange' ? 'Working…' : 'Exchange token'}
              </button>
              <button className="btn" onClick={() => runAction('plaid-sync-all', () => syncPlaid())} disabled={!!busyAction}>
                {busyAction === 'plaid-sync-all' ? 'Working…' : 'Sync all Plaid'}
              </button>
            </div>
            {plaidLinkToken && (
              <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)', wordBreak: 'break-all' }}>
                Link token: {plaidLinkToken}
              </div>
            )}
          </div>

          <div className="card" style={{ padding: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 'var(--s-2)' }}>Google Sheets CSV feed (optional)</div>
            <div className="field">
              <label>Feed name</label>
              <input value={sheetsName} onChange={e => setSheetsName(e.target.value)} placeholder="e.g. Household Checking Feed" />
            </div>
            <div className="field">
              <label>CSV URL</label>
              <input value={sheetsCsvUrl} onChange={e => setSheetsCsvUrl(e.target.value)} placeholder="https://docs.google.com/...&output=csv" />
            </div>
            <div className="field">
              <label>Bind to account</label>
              <select value={sheetsAccountId} onChange={e => setSheetsAccountId(e.target.value)}>
                <option value="">Select account</option>
                {accounts?.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Mapping preset</label>
              <select value={sheetsMappingPreset} onChange={e => setSheetsMappingPreset(e.target.value)}>
                <option value="default">Default (lowercase headers)</option>
                <option value="bank_statement">Bank statement style</option>
                <option value="brokerage_export">Brokerage export style</option>
              </select>
            </div>
            <div className="flex gap-8">
              <button className="btn" onClick={() => runAction('sheets-validate', validateSheetsFeed)} disabled={!sheetsCsvUrl.trim() || !!busyAction}>
                {busyAction === 'sheets-validate' ? 'Working…' : 'Validate feed'}
              </button>
              <button
                className="btn btn-primary"
                onClick={() => runAction('sheets-add', addSheetsFeed)}
                disabled={!sheetsName.trim() || !sheetsCsvUrl.trim() || !sheetsAccountId || !!busyAction}
              >
                {busyAction === 'sheets-add' ? 'Working…' : 'Add feed'}
              </button>
              <button className="btn" onClick={() => runAction('sheets-sync-all', () => syncSheets())} disabled={!!busyAction}>
                {busyAction === 'sheets-sync-all' ? 'Working…' : 'Sync all Sheets'}
              </button>
              <button className="btn" onClick={() => refetchIntegrations()} disabled={!!busyAction}>Refresh status</button>
            </div>
            {sheetsValidation && <div style={{ marginTop: 10, color: 'var(--text-3)', fontSize: 'var(--fs-sm)' }}>{sheetsValidation}</div>}
          </div>
        </div>

        {integrationStatus?.connections?.length ? (
          <div style={{ marginTop: 18, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Connection status</div>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Last sync</th>
                  <th>Error</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {integrationStatus.connections.map(conn => (
                  <tr key={conn.id}>
                    <td style={{ textTransform: 'capitalize' }}>{conn.provider}</td>
                    <td>{conn.name}</td>
                    <td>{conn.status}</td>
                    <td>{conn.last_sync_at ? new Date(conn.last_sync_at).toLocaleString() : '—'}</td>
                    <td style={{ maxWidth: 240, color: 'var(--text-3)' }}>{conn.last_error ?? '—'}</td>
                    <td>
                      <div className="flex gap-8">
                        {conn.provider === 'plaid' && (
                          <>
                            <button className="btn btn-sm" onClick={() => runAction(`plaid-sync-${conn.id}`, () => syncPlaid(conn.id))} disabled={!!busyAction}>Sync</button>
                            <button className="btn btn-sm" onClick={() => runAction(`plaid-relink-${conn.id}`, () => setPlaidRelink(conn.id))} disabled={!!busyAction}>Relink</button>
                            <button className="btn btn-sm" onClick={() => runAction(`plaid-disconnect-${conn.id}`, () => disconnectPlaid(conn.id))} disabled={!!busyAction}>Disconnect</button>
                          </>
                        )}
                        {conn.provider === 'sheets' && (
                          <>
                            <button className="btn btn-sm" onClick={() => runAction(`sheets-sync-${conn.id}`, () => syncSheets(conn.id))} disabled={!!busyAction}>Sync</button>
                            <button className="btn btn-sm" onClick={() => runAction(`sheets-disable-${conn.id}`, () => disableSheetsFeed(conn.id))} disabled={!!busyAction}>Disable</button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      {/* ── Data ── */}
      <div className="section-label mb-16">Data</div>
      <div className="flex gap-8">
        <button className="btn" onClick={seedDemoData}>
          Load fake demo data
        </button>
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

      {confirmPending && (
        <Confirm
          message={confirmPending.message}
          detail={confirmPending.detail}
          destructive
          confirmLabel="Remove"
          onConfirm={confirmPending.onConfirm}
          onCancel={() => setConfirmPending(null)}
        />
      )}
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
