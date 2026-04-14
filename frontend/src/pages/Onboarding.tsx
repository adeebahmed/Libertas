import { useState } from 'react'
import { api } from '../api/client'

type DataMethod = 'manual' | 'csv' | 'both'
type FireType = 'lean' | 'regular' | 'fat'

const CASH_LIKE_TYPES = new Set(['checking', 'savings'])

export default function Onboarding({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(1)
  const [method, setMethod] = useState<DataMethod>('manual')
  const [accountName, setAccountName] = useState('')
  const [accountType, setAccountType] = useState('checking')
  const [openingBalance, setOpeningBalance] = useState('')
  const [fireType, setFireType] = useState<FireType | ''>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleNext() {
    setError(null)
    if (step === 3) {
      if (method !== 'csv' && !accountName.trim()) {
        setError('Add account name or choose CSV-only method.')
        return
      }

      if (accountName.trim()) {
        try {
          setBusy(true)
          const account = await api.post<{ id: number; type: string }>('/accounts', {
            name: accountName.trim(),
            type: accountType,
          })
          if (openingBalance && CASH_LIKE_TYPES.has(account.type)) {
            await api.post(`/accounts/${account.id}/balance`, {
              balance: Number(openingBalance),
              date: new Date().toISOString().slice(0, 10),
            })
          }
        } catch (e: any) {
          setError(e.message ?? 'Could not create account')
          setBusy(false)
          return
        } finally {
          setBusy(false)
        }
      }
    }

    if (step === 4) {
      try {
        setBusy(true)
        if (fireType) {
          await api.put('/settings/fire_type', { value: fireType })
        }
        await api.put('/settings/onboarding_complete', { value: true })
        onComplete()
      } catch (e: any) {
        setError(e.message ?? 'Could not complete onboarding')
      } finally {
        setBusy(false)
      }
      return
    }

    setStep((s) => s + 1)
  }

  function handleBack() {
    setError(null)
    setStep((s) => Math.max(1, s - 1))
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 0 40px' }}>
      <h1 className="page-title">Welcome to Libertas</h1>
      <p style={{ color: 'var(--text-2)', marginTop: -10, marginBottom: 24 }}>
        Your finances, your machine, your control.
      </p>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="section-label mb-8">Privacy by default</div>
        <div style={{ color: 'var(--text-2)', fontSize: 14 }}>
          Everything stays local. No cloud account required. No institution credentials stored.
        </div>
      </div>

      <div className="card">
        <div className="section-label mb-16">Step {step} of 4</div>

        {step === 1 && (
          <div>
            <h2 style={{ margin: '0 0 8px', fontSize: 20 }}>Start in under 3 minutes</h2>
            <p style={{ color: 'var(--text-2)', margin: 0 }}>
              We will set data method, add first account, then optional FIRE target.
            </p>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 style={{ margin: '0 0 12px', fontSize: 20 }}>Choose data method</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {[
                ['manual', 'Manual entry', 'Fast start with account + balance.'],
                ['csv', 'CSV import', 'Use exported statements now.'],
                ['both', 'Both', 'Manual now, CSV later.'],
              ].map(([value, label, desc]) => (
                <label key={value} className="card" style={{ padding: 12, cursor: 'pointer' }}>
                  <input
                    type="radio"
                    checked={method === value}
                    onChange={() => setMethod(value as DataMethod)}
                    style={{ marginRight: 8 }}
                  />
                  <strong>{label}</strong>
                  <div style={{ fontSize: 13, color: 'var(--text-2)', marginTop: 4 }}>{desc}</div>
                </label>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 style={{ margin: '0 0 12px', fontSize: 20 }}>Add first account</h2>
            {method === 'csv' && (
              <div style={{ fontSize: 14, color: 'var(--text-2)', marginBottom: 12 }}>
                CSV-only selected. You can skip this and import from Import page after onboarding.
              </div>
            )}
            <div className="settings-inline-form" style={{ gridTemplateColumns: '1.4fr 1fr 1fr' }}>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Account name</label>
                <input
                  value={accountName}
                  onChange={(e) => setAccountName(e.target.value)}
                  placeholder="Main Checking"
                />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Type</label>
                <select value={accountType} onChange={(e) => setAccountType(e.target.value)}>
                  <option value="checking">Checking</option>
                  <option value="savings">Savings</option>
                  <option value="brokerage">Brokerage</option>
                  <option value="crypto">Crypto</option>
                </select>
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Opening balance (optional)</label>
                <input
                  type="number"
                  value={openingBalance}
                  onChange={(e) => setOpeningBalance(e.target.value)}
                  placeholder="5000"
                />
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div>
            <h2 style={{ margin: '0 0 12px', fontSize: 20 }}>Optional FIRE goal</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {[
                ['lean', 'Lean FIRE', 'Bare-minimum expenses, earliest timeline.'],
                ['regular', 'Regular FIRE', 'Current lifestyle baseline.'],
                ['fat', 'Fat FIRE', 'Higher lifestyle target.'],
              ].map(([value, label, desc]) => (
                <label key={value} className="card" style={{ padding: 12, cursor: 'pointer' }}>
                  <input
                    type="radio"
                    checked={fireType === value}
                    onChange={() => setFireType(value as FireType)}
                    style={{ marginRight: 8 }}
                  />
                  <strong>{label}</strong>
                  <div style={{ fontSize: 13, color: 'var(--text-2)', marginTop: 4 }}>{desc}</div>
                </label>
              ))}
            </div>
            <button
              type="button"
              className="btn btn-secondary mt-16"
              onClick={() => setFireType('')}
            >
              Skip for now
            </button>
          </div>
        )}

        {error && (
          <div style={{ color: 'var(--red)', marginTop: 14, fontSize: 13 }}>{error}</div>
        )}

        <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
          {step > 1 && (
            <button type="button" className="btn btn-secondary" onClick={handleBack} disabled={busy}>
              Back
            </button>
          )}
          <button type="button" className="btn" onClick={handleNext} disabled={busy}>
            {step === 4 ? 'Finish Setup' : 'Continue'}
          </button>
        </div>
      </div>
    </div>
  )
}
