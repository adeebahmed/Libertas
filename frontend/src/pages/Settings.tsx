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

function ApiKeyLabel({ label, href }: { label: string; href: string }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <span>{label}</span>
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        style={{ fontSize: 'var(--fs-xs)', color: 'var(--accent)', textDecoration: 'none', whiteSpace: 'nowrap' }}
        title="Open provider page in a new tab"
      >
        Get key ↗
      </a>
    </label>
  )
}

export default function Settings() {
  const { data: settings, refetch: refetchSettings } = useApi<Record<string, unknown>>(() => api.get('/settings'), [])

  const [claudeKey, setClaudeKey] = useState('')
  const [newsApiKey, setNewsApiKey] = useState('')
  const [plaidClientId, setPlaidClientId] = useState('')
  const [plaidSecret, setPlaidSecret] = useState('')
  const [plaidEnv, setPlaidEnv] = useState('sandbox')
  const [encryptionMode, setEncryptionMode] = useState<'keychain' | 'passphrase'>('keychain')
  const [passphrase, setPassphrase] = useState('')
  const [passphraseConfirm, setPassphraseConfirm] = useState('')
  const [passphraseSet, setPassphraseSet] = useState(false)

  const [confirmPending, setConfirmPending] = useState<{ message: string; detail?: string; onConfirm: () => void } | null>(null)
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!settings) return
    setClaudeKey(String(settings.claude_api_key ?? ''))
    setNewsApiKey(String(settings.news_api_key ?? ''))
    setPlaidClientId(String(settings.plaid_client_id ?? ''))
    setPlaidSecret(String(settings.plaid_secret ?? ''))
    setPlaidEnv(String(settings.plaid_env ?? 'sandbox'))
    setEncryptionMode((settings.encryption_mode as 'keychain' | 'passphrase') ?? 'keychain')
    setPassphraseSet(Boolean(settings.encryption_passphrase_set))
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
            <ApiKeyLabel label="Claude API key (optional)" href="https://console.anthropic.com/settings/keys" />
            <input type="password" value={claudeKey} onChange={e => setClaudeKey(e.target.value)}
              onBlur={() => saveSetting('claude_api_key', claudeKey)} placeholder="sk-ant-…" />
          </div>
          <div className="field">
            <ApiKeyLabel label="News API key (optional)" href="https://newsapi.org/account" />
            <input type="password" value={newsApiKey} onChange={e => setNewsApiKey(e.target.value)}
              onBlur={() => saveSetting('news_api_key', newsApiKey)} placeholder="NewsAPI key" />
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)', marginTop: 20, paddingTop: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Plaid (optional)</div>
          <div className="grid-3">
            <div className="field">
              <ApiKeyLabel label="Client ID" href="https://dashboard.plaid.com/team/keys" />
              <input value={plaidClientId} onChange={e => setPlaidClientId(e.target.value)}
                onBlur={() => saveSetting('plaid_client_id', plaidClientId)} placeholder="Plaid client_id" />
            </div>
            <div className="field">
              <ApiKeyLabel label="Secret" href="https://dashboard.plaid.com/team/keys" />
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

      {/* ── Data Security ── */}
      <div className="section-label mb-16">Data Security</div>
      <div className="card mb-32">
        <p style={{ margin: '0 0 20px', color: 'var(--text-2)', fontSize: 'var(--fs-sm)', lineHeight: 1.6 }}>
          All financial data is encrypted before it's saved. The database is unreadable without your key — even if someone steals the file.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Keychain option */}
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer', padding: '14px 16px', borderRadius: 'var(--r)', border: `1px solid ${encryptionMode === 'keychain' ? 'var(--accent)' : 'var(--border)'}`, background: encryptionMode === 'keychain' ? 'color-mix(in srgb, var(--accent) 6%, transparent)' : 'transparent', transition: 'all 0.15s' }}>
            <input type="radio" name="encryption_mode" value="keychain" checked={encryptionMode === 'keychain'}
              onChange={() => { setEncryptionMode('keychain'); saveSetting('encryption_mode', 'keychain') }}
              style={{ marginTop: 2, accentColor: 'var(--accent)' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: 'var(--fs-base)', marginBottom: 3 }}>
                macOS Keychain <span style={{ fontWeight: 400, fontSize: 'var(--fs-xs)', color: 'var(--accent)', marginLeft: 6 }}>Default</span>
              </div>
              <div style={{ color: 'var(--text-2)', fontSize: 'var(--fs-sm)', lineHeight: 1.5 }}>
                Your encryption key is stored securely by macOS and unlocks automatically with Touch ID or your login password. No extra steps required.
              </div>
            </div>
          </label>

          {/* Passphrase option */}
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer', padding: '14px 16px', borderRadius: 'var(--r)', border: `1px solid ${encryptionMode === 'passphrase' ? 'var(--accent)' : 'var(--border)'}`, background: encryptionMode === 'passphrase' ? 'color-mix(in srgb, var(--accent) 6%, transparent)' : 'transparent', transition: 'all 0.15s' }}>
            <input type="radio" name="encryption_mode" value="passphrase" checked={encryptionMode === 'passphrase'}
              onChange={() => { setEncryptionMode('passphrase'); saveSetting('encryption_mode', 'passphrase') }}
              style={{ marginTop: 2, accentColor: 'var(--accent)' }} />
            <div style={{ width: '100%' }}>
              <div style={{ fontWeight: 600, fontSize: 'var(--fs-base)', marginBottom: 3 }}>
                Passphrase <span style={{ fontWeight: 400, fontSize: 'var(--fs-xs)', color: 'var(--text-3)', marginLeft: 6 }}>Maximum security</span>
              </div>
              <div style={{ color: 'var(--text-2)', fontSize: 'var(--fs-sm)', lineHeight: 1.5, marginBottom: encryptionMode === 'passphrase' ? 16 : 0 }}>
                You control the key. Libertas will ask for your passphrase each time you open it. If you lose the passphrase, the data cannot be recovered.
              </div>
              {encryptionMode === 'passphrase' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <input type="password" value={passphrase} onChange={e => setPassphrase(e.target.value)}
                    placeholder="Enter passphrase" style={{ maxWidth: 320 }} />
                  <input type="password" value={passphraseConfirm} onChange={e => setPassphraseConfirm(e.target.value)}
                    placeholder="Confirm passphrase" style={{ maxWidth: 320 }} />
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <button className="btn btn-primary" style={{ width: 'fit-content' }}
                      disabled={!passphrase || passphrase !== passphraseConfirm}
                      onClick={async () => {
                        await saveSetting('encryption_passphrase_set', true)
                        setPassphraseSet(true)
                        setPassphrase('')
                        setPassphraseConfirm('')
                        showToast('Passphrase saved')
                      }}>
                      Set passphrase
                    </button>
                    {passphraseSet && <span style={{ fontSize: 'var(--fs-sm)', color: 'var(--pos)' }}>● Active</span>}
                  </div>
                  {passphrase && passphraseConfirm && passphrase !== passphraseConfirm && (
                    <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--neg)' }}>Passphrases don't match</div>
                  )}
                </div>
              )}
            </div>
          </label>
        </div>

        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)', fontSize: 'var(--fs-sm)', color: 'var(--text-3)' }}>
          Encryption: AES-256-GCM · Key derivation: Argon2id · Claude only decrypts at runtime, never stores plaintext
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
