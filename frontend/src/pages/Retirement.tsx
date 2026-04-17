import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Projection, RetirementPlan } from '../types'
import { TerminalLineChart } from '../components/Chart'

function usd(n: number) {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}k`
  return `$${n.toFixed(0)}`
}

function usdFull(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

type Tab = 'scenarios' | 'plan' | 'settings'

export default function RetirementPage() {
  const [tab, setTab] = useState<Tab>('plan')
  const [contribution, setContribution] = useState(2000)
  const [years, setYears] = useState(20)
  const [conservative, setConservative] = useState(4)
  const [moderate, setModerate] = useState(7)
  const [aggressive, setAggressive] = useState(10)

  const { data: settings, refetch: refetchSettings } = useApi<Record<string, unknown>>(() => api.get('/settings'), [])
  const [expenses, setExpenses] = useState('')
  const [risk, setRisk] = useState('moderate')
  const [birthYear, setBirthYear] = useState('')
  const [retirementAge, setRetirementAge] = useState('65')
  const [monthlyContribution, setMonthlyContribution] = useState('')
  const [retirementTarget, setRetirementTarget] = useState('')
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!settings) return
    setExpenses(String(settings.monthly_expenses ?? ''))
    setRisk(String(settings.risk_profile ?? 'moderate'))
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

  const qs = `?monthly_contribution=${contribution}&years=${years}&conservative_rate=${conservative / 100}&moderate_rate=${moderate / 100}&aggressive_rate=${aggressive / 100}`
  const { data: scenarios, loading: scenariosLoading } = useApi<Projection>(() => api.get(`/retirement${qs}`), [contribution, years, conservative, moderate, aggressive])
  const { data: plan, loading: planLoading } = useApi<RetirementPlan>(() => api.get('/retirement/plan'), [])

  const chartData = scenarios
    ? scenarios.scenarios.conservative.map((_, i) => ({
        year: i,
        Conservative: scenarios.scenarios.conservative[i].value,
        Moderate: scenarios.scenarios.moderate[i].value,
        Aggressive: scenarios.scenarios.aggressive[i].value,
      }))
    : []

  const planChartData = plan
    ? plan.scenarios.conservative.map((_, i) => ({
        year: i,
        Conservative: plan.scenarios.conservative[i].value,
        Moderate: plan.scenarios.moderate[i].value,
        Aggressive: plan.scenarios.aggressive[i].value,
        Target: plan.target,
      }))
    : []

  const last = (arr: { value: number }[]) => arr[arr.length - 1]?.value ?? 0
  const finals = scenarios ? {
    conservative: last(scenarios.scenarios.conservative),
    moderate:     last(scenarios.scenarios.moderate),
    aggressive:   last(scenarios.scenarios.aggressive),
  } : null
  const planInitialLoading = planLoading && !plan
  const scenariosInitialLoading = scenariosLoading && !scenarios

  return (
    <div>
      <h1 className="page-title">Retirement</h1>

      <div className="tabs mb-24">
        <button className={`tab-btn${tab === 'plan' ? ' active' : ''}`} onClick={() => setTab('plan')}>Retirement Plan</button>
        <button className={`tab-btn${tab === 'scenarios' ? ' active' : ''}`} onClick={() => setTab('scenarios')}>Scenarios</button>
        <button className={`tab-btn${tab === 'settings' ? ' active' : ''}`} onClick={() => setTab('settings')}>Settings</button>
      </div>

      {tab === 'plan' && planInitialLoading && (
        <div className="empty">
          <span className="spinner" aria-label="Loading retirement plan" />
          <div className="empty-sub" style={{ marginTop: 10 }}>Loading retirement plan…</div>
        </div>
      )}

      {tab === 'plan' && plan && (
        <>
          {plan.on_track && (
            <div className="card mb-24" style={{ borderTop: `3px solid ${plan.on_track.on_track ? 'var(--pos)' : 'var(--neg)'}` }}>
              <div className="flex-between mb-16">
                <div>
                  <div className="section-label mb-4">Retirement Projection</div>
                  <div style={{ fontSize: 'var(--fs-base)', color: 'var(--text-2)' }}>
                    {plan.on_track.years_to_retire} years to retirement · ${plan.monthly_contribution.toLocaleString()}/mo contribution
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{
                    fontSize: 'var(--fs-sm)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
                    color: plan.on_track.on_track ? 'var(--pos)' : 'var(--neg)',
                    marginBottom: 4,
                  }}>
                    {plan.on_track.on_track ? '✓ On Track' : '⚠ Behind'}
                  </div>
                  <div className="num" style={{ fontSize: 'var(--fs-base)', color: 'var(--text-2)' }}>
                    {plan.on_track.on_track
                      ? `${usd(plan.on_track.surplus)} surplus`
                      : `${usd(plan.on_track.shortfall)} shortfall`}
                  </div>
                </div>
              </div>
              <div className="grid-3">
                <div>
                  <div className="section-label mb-4">Current Balance</div>
                  <div className="num-mid">{usdFull(plan.current_balance)}</div>
                </div>
                <div>
                  <div className="section-label mb-4">Projected at Retirement</div>
                  <div className="num-mid" style={{ color: plan.on_track.on_track ? 'var(--pos)' : 'var(--neg)' }}>
                    {usdFull(plan.on_track.projected_at_retirement)}
                  </div>
                </div>
                <div>
                  <div className="section-label mb-4">Target</div>
                  <div className="num-mid">{usdFull(plan.target)}</div>
                </div>
              </div>
              {!plan.on_track.on_track && plan.needed_monthly_contribution && (
                <div style={{ marginTop: 16, padding: '12px 16px', background: 'var(--bg-2)', borderRadius: 'var(--r)', fontSize: 'var(--fs-base)', color: 'var(--text-2)' }}>
                  To hit your target by retirement: contribute <strong style={{ color: 'var(--text)' }}>{usdFull(plan.needed_monthly_contribution)}/mo</strong> (vs current {usdFull(plan.monthly_contribution)}/mo)
                </div>
              )}
            </div>
          )}

          {!plan.on_track && (
            <div className="card mb-24">
              <div className="empty-sub">Set your birth year, retirement age, and monthly contribution in the <button className="btn btn-sm" style={{ display: 'inline', padding: '2px 8px' }} onClick={() => setTab('settings')}>Settings tab</button> to see your personalized plan.</div>
              <div className="grid-2 mt-16">
                <div>
                  <div className="section-label mb-4">Current Balance</div>
                  <div className="num-mid">{usdFull(plan.current_balance)}</div>
                </div>
                <div>
                  <div className="section-label mb-4">FIRE Target (4% rule)</div>
                  <div className="num-mid">{usdFull(plan.target)}</div>
                </div>
              </div>
              {plan.years_to_target && (
                <div style={{ marginTop: 12, fontSize: 'var(--fs-base)', color: 'var(--text-2)' }}>
                  At current pace: target reached in ~{plan.years_to_target} years
                </div>
              )}
            </div>
          )}

          <div className="card">
            <div className="section-label mb-16">Growth to target</div>
            <TerminalLineChart
              data={planChartData}
              height={320}
              formatter={usd}
              reference={{ y: plan.target, label: 'Target' }}
              series={[
                { dataKey: 'Conservative', stroke: 'var(--pos)' },
                { dataKey: 'Moderate', stroke: 'var(--accent)', strokeWidth: 2 },
                { dataKey: 'Aggressive', stroke: 'var(--neg)', strokeDasharray: '4 2' },
              ]}
            />
          </div>
        </>
      )}

      {tab === 'scenarios' && (
        <>
          <div className="card mb-24" style={{ padding: 'var(--s-5)' }}>
            <div className="retirement-controls-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--s-5)' }}>
              {[
                { label: 'Monthly add ($)', value: contribution, set: setContribution, step: 100 },
                { label: 'Years', value: years, set: setYears, step: 1 },
                { label: 'Conservative (%)', value: conservative, set: setConservative, step: 0.5 },
                { label: 'Moderate (%)', value: moderate, set: setModerate, step: 0.5 },
                { label: 'Aggressive (%)', value: aggressive, set: setAggressive, step: 0.5 },
              ].map(({ label, value, set, step }) => (
                <div key={label} className="field" style={{ marginBottom: 0 }}>
                  <label>{label}</label>
                  <input type="number" value={value} step={step} onChange={(e) => set(Number(e.target.value))} />
                </div>
              ))}
            </div>
          </div>

          {finals && scenarios && (
            <div className="grid-3 mb-24">
              {([
                ['Conservative', finals.conservative, 'var(--pos)', conservative],
                ['Moderate',     finals.moderate,     'var(--accent)', moderate],
                ['Aggressive',   finals.aggressive,   'var(--neg)', aggressive],
              ] as const).map(([name, val, color, rate]) => (
                <div key={name} className="card" style={{ borderTop: `3px solid ${color}`, paddingTop: 18 }}>
                  <div className="section-label mb-8">{name} · {rate}% / yr</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-2xl)', letterSpacing: -0.5, color: 'var(--text)', marginBottom: 6 }}>
                    {usdFull(val as number)}
                  </div>
                  <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                    in {years} yrs from {usdFull(scenarios.current_balance)}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="card">
            <div className="section-label mb-16">Growth scenarios</div>
            {scenariosInitialLoading ? (
              <div className="empty">
                <span className="spinner" aria-label="Loading growth scenarios" />
                <div className="empty-sub" style={{ marginTop: 10 }}>Loading growth scenarios…</div>
              </div>
            ) : chartData.length > 0 ? (
              <TerminalLineChart
                data={chartData}
                height={360}
                formatter={usd}
                series={[
                  { dataKey: 'Conservative', stroke: 'var(--pos)' },
                  { dataKey: 'Moderate', stroke: 'var(--accent)', strokeWidth: 2 },
                  { dataKey: 'Aggressive', stroke: 'var(--neg)', strokeDasharray: '4 2' },
                ]}
              />
            ) : (
              <div className="empty"><div className="empty-sub">Adjust parameters above</div></div>
            )}
          </div>
        </>
      )}

      {tab === 'settings' && (
        <>
          <div className="section-label mb-16">Retirement Settings</div>
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
            </div>
          </div>
        </>
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
