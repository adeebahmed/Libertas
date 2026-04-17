import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import Confirm from '../components/Confirm'
import { useTheme, type Theme } from '../theme'

type SeedDemoResponse = {
  ok: boolean
  rows_imported: number
  rows_skipped: number
  errors: { file: string; error: string }[]
}

export default function Settings() {
  const { data: settings, refetch: refetchSettings } = useApi<Record<string, unknown>>(() => api.get('/settings'), [])

  const [claudeKey, setClaudeKey] = useState('')
  const [plaidClientId, setPlaidClientId] = useState('')
  const [plaidSecret, setPlaidSecret] = useState('')
  const [plaidEnv, setPlaidEnv] = useState('sandbox')

  const [confirmPending, setConfirmPending] = useState<{ message: string; detail?: string; onConfirm: () => void } | null>(null)
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!settings) return
    setClaudeKey(String(settings.claude_api_key ?? ''))
    setPlaidClientId(String(settings.plaid_client_id ?? ''))
    setPlaidSecret(String(settings.plaid_secret ?? ''))
    setPlaidEnv(String(settings.plaid_env ?? 'sandbox'))
  }, [settings])

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 2500) }

  const saveSetting = async (key: string, value: unknown) => {
    await api.put(`/settings/${key}`, { value })
    refetchSettings()
    showToast('Saved')
  }

  const seedDemoData = async () => {
    const result = await api.post<SeedDemoResponse>('/settings/seed-demo')
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

      {/* ── API Keys ── */}
      <div className="section-label mb-16">API Keys</div>
      <div className="card mb-32">
        <div className="grid-2">
          <div className="field">
            <label>Claude API key (optional)</label>
            <input type="password" value={claudeKey} onChange={e => setClaudeKey(e.target.value)}
              onBlur={() => saveSetting('claude_api_key', claudeKey)} placeholder="sk-ant-…" />
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)', marginTop: 20, paddingTop: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Plaid (optional)</div>
          <div className="grid-3">
            <div className="field">
              <label>Client ID</label>
              <input value={plaidClientId} onChange={e => setPlaidClientId(e.target.value)}
                onBlur={() => saveSetting('plaid_client_id', plaidClientId)} placeholder="Plaid client_id" />
            </div>
            <div className="field">
              <label>Secret</label>
              <input type="password" value={plaidSecret} onChange={e => setPlaidSecret(e.target.value)}
                onBlur={() => saveSetting('plaid_secret', plaidSecret)} placeholder="Plaid secret" />
            </div>
            <div className="field">
              <label>Environment</label>
              <select value={plaidEnv} onChange={e => { setPlaidEnv(e.target.value); saveSetting('plaid_env', e.target.value) }}>
                <option value="sandbox">Sandbox</option>
                <option value="development">Development</option>
                <option value="production">Production</option>
              </select>
            </div>
          </div>
        </div>
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
