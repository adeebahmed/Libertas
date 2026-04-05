import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Projection, RetirementPlan } from '../types'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

function usd(n: number) {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}k`
  return `$${n.toFixed(0)}`
}

function usdFull(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#1c1a14', border: '1px solid #26231b', borderRadius: 8, padding: '10px 14px', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
      <div style={{ color: '#5c5444', marginBottom: 6 }}>Year {label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color, marginBottom: 2 }}>
          {p.name}: {usdFull(p.value)}
        </div>
      ))}
    </div>
  )
}

type Tab = 'scenarios' | 'plan'

export default function RetirementPage() {
  const [tab, setTab] = useState<Tab>('plan')
  const [contribution, setContribution] = useState(2000)
  const [years, setYears] = useState(20)
  const [conservative, setConservative] = useState(4)
  const [moderate, setModerate] = useState(7)
  const [aggressive, setAggressive] = useState(10)

  const qs = `?monthly_contribution=${contribution}&years=${years}&conservative_rate=${conservative / 100}&moderate_rate=${moderate / 100}&aggressive_rate=${aggressive / 100}`
  const { data: scenarios } = useApi<Projection>(() => api.get(`/retirement${qs}`), [contribution, years, conservative, moderate, aggressive])
  const { data: plan } = useApi<RetirementPlan>(() => api.get('/retirement/plan'), [])

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

  return (
    <div>
      <h1 className="page-title">Retirement</h1>

      <div className="tabs mb-24">
        <button className={`tab${tab === 'plan' ? ' active' : ''}`} onClick={() => setTab('plan')}>Retirement Plan</button>
        <button className={`tab${tab === 'scenarios' ? ' active' : ''}`} onClick={() => setTab('scenarios')}>Scenarios</button>
      </div>

      {tab === 'plan' && plan && (
        <>
          {/* On-track status */}
          {plan.on_track && (
            <div className="card mb-24" style={{ borderTop: `3px solid ${plan.on_track.on_track ? 'var(--green)' : 'var(--red)'}` }}>
              <div className="flex-between mb-16">
                <div>
                  <div className="section-label mb-4">Retirement Projection</div>
                  <div style={{ fontSize: 13, color: 'var(--text-2)' }}>
                    {plan.on_track.years_to_retire} years to retirement · ${plan.monthly_contribution.toLocaleString()}/mo contribution
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{
                    fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
                    color: plan.on_track.on_track ? 'var(--green)' : 'var(--red)',
                    marginBottom: 4,
                  }}>
                    {plan.on_track.on_track ? '✓ On Track' : '⚠ Behind'}
                  </div>
                  <div className="num" style={{ fontSize: 13, color: 'var(--text-2)' }}>
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
                  <div className="num-mid" style={{ color: plan.on_track.on_track ? 'var(--green)' : 'var(--red)' }}>
                    {usdFull(plan.on_track.projected_at_retirement)}
                  </div>
                </div>
                <div>
                  <div className="section-label mb-4">Target</div>
                  <div className="num-mid">{usdFull(plan.target)}</div>
                </div>
              </div>
              {!plan.on_track.on_track && plan.needed_monthly_contribution && (
                <div style={{ marginTop: 16, padding: '12px 16px', background: 'var(--bg-elevated)', borderRadius: 6, fontSize: 13, color: 'var(--text-2)' }}>
                  To hit your target by retirement: contribute <strong style={{ color: 'var(--text)' }}>{usdFull(plan.needed_monthly_contribution)}/mo</strong> (vs current {usdFull(plan.monthly_contribution)}/mo)
                </div>
              )}
            </div>
          )}

          {!plan.on_track && (
            <div className="card mb-24">
              <div className="empty-sub">Set your birth year, retirement age, and monthly contribution in Settings to see your personalized plan.</div>
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
                <div style={{ marginTop: 12, fontSize: 13, color: 'var(--text-2)' }}>
                  At current pace: target reached in ~{plan.years_to_target} years
                </div>
              )}
            </div>
          )}

          {/* Plan chart */}
          <div className="card">
            <div className="section-label mb-16">Growth to target</div>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={planChartData} margin={{ top: 4, right: 4, left: -4, bottom: 0 }}>
                <XAxis dataKey="year" tick={{ fill: '#5c5444', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#5c5444', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={usd} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={plan.target} stroke="var(--gold)" strokeDasharray="4 2" label={{ value: 'Target', fill: 'var(--gold)', fontSize: 11 }} />
                <Line type="monotone" dataKey="Conservative" stroke="#5cad7a" strokeWidth={1.5} dot={false} />
                <Line type="monotone" dataKey="Moderate"     stroke="#c9a96e" strokeWidth={2}   dot={false} />
                <Line type="monotone" dataKey="Aggressive"   stroke="#c95f52" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {tab === 'scenarios' && (
        <>
          <div className="card mb-24" style={{ padding: '20px 24px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 20 }}>
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
                ['Conservative', finals.conservative, '#5cad7a', conservative],
                ['Moderate',     finals.moderate,     '#c9a96e', moderate],
                ['Aggressive',   finals.aggressive,   '#c95f52', aggressive],
              ] as const).map(([name, val, color, rate]) => (
                <div key={name} className="card" style={{ borderTop: `3px solid ${color}`, paddingTop: 18 }}>
                  <div className="section-label mb-8">{name} · {rate}% / yr</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 26, letterSpacing: -0.5, color: 'var(--text)', marginBottom: 6 }}>
                    {usdFull(val as number)}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                    in {years} yrs from {usdFull(scenarios.current_balance)}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="card">
            <div className="section-label mb-16">Growth scenarios</div>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={360}>
                <LineChart data={chartData} margin={{ top: 4, right: 4, left: -4, bottom: 0 }}>
                  <XAxis dataKey="year" tick={{ fill: '#5c5444', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#5c5444', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={usd} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="Conservative" stroke="#5cad7a" strokeWidth={1.5} dot={false} />
                  <Line type="monotone" dataKey="Moderate"     stroke="#c9a96e" strokeWidth={2}   dot={false} />
                  <Line type="monotone" dataKey="Aggressive"   stroke="#c95f52" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty"><div className="empty-sub">Adjust parameters above</div></div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
