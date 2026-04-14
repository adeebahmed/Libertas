import { useMemo, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import type { FireProjection, Projection, RetirementOverview } from '../types'

type Tab = 'overview' | 'fire' | 'scenarios'
type FireType = 'lean' | 'regular' | 'fat' | 'coast' | 'barista'

function usd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function compact(n: number) {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}k`
  return usd(n)
}

export default function RetirementPage() {
  const [tab, setTab] = useState<Tab>('overview')
  const [fireType, setFireType] = useState<FireType>('regular')
  const [monthlyContribution, setMonthlyContribution] = useState(2000)
  const [expectedReturn, setExpectedReturn] = useState(7)
  const [swr, setSwr] = useState(4)

  const [scenarioContribution, setScenarioContribution] = useState(2000)
  const [scenarioYears, setScenarioYears] = useState(20)
  const [conservative, setConservative] = useState(4)
  const [moderate, setModerate] = useState(7)
  const [aggressive, setAggressive] = useState(10)

  const fireQs = useMemo(
    () => `?fire_type=${fireType}&monthly_contribution=${monthlyContribution}&expected_return=${expectedReturn / 100}&safe_withdrawal_rate=${swr / 100}`,
    [fireType, monthlyContribution, expectedReturn, swr],
  )
  const scenarioQs = useMemo(
    () =>
      `?monthly_contribution=${scenarioContribution}&years=${scenarioYears}&conservative_rate=${conservative / 100}&moderate_rate=${moderate / 100}&aggressive_rate=${aggressive / 100}`,
    [scenarioContribution, scenarioYears, conservative, moderate, aggressive],
  )

  const { data: overview } = useApi<RetirementOverview>(() => api.get('/retirement/overview'), [])
  const { data: fire } = useApi<FireProjection>(() => api.get(`/retirement/fire${fireQs}`), [fireQs])
  const { data: recommendation } = useApi<{ recommended_fire_type: string; reason: string }>(
    () => api.get('/retirement/fire/recommend'),
    [],
  )
  const { data: scenarios } = useApi<Projection>(() => api.get(`/retirement${scenarioQs}`), [scenarioQs])

  const scenarioChartData = useMemo(
    () =>
      scenarios
        ? scenarios.scenarios.conservative.map((_, i) => ({
            year: i,
            Conservative: scenarios.scenarios.conservative[i].value,
            Moderate: scenarios.scenarios.moderate[i].value,
            Aggressive: scenarios.scenarios.aggressive[i].value,
          }))
        : [],
    [scenarios],
  )

  return (
    <div>
      <h1 className="page-title">Retirement & FIRE</h1>

      <div className="tabs mb-24">
        <button className={`tab${tab === 'overview' ? ' active' : ''}`} onClick={() => setTab('overview')}>Overview</button>
        <button className={`tab${tab === 'fire' ? ' active' : ''}`} onClick={() => setTab('fire')}>FIRE Calculator</button>
        <button className={`tab${tab === 'scenarios' ? ' active' : ''}`} onClick={() => setTab('scenarios')}>Scenarios</button>
      </div>

      {tab === 'overview' && overview && (
        <>
          <div className="grid-3 mb-24">
            <div className="card">
              <div className="section-label mb-8">Retirement Assets</div>
              <div className="num-mid">{usd(overview.total_retirement_assets)}</div>
            </div>
            <div className="card">
              <div className="section-label mb-8">Readiness</div>
              <div className="num-mid">{overview.readiness.percent.toFixed(1)}%</div>
              <div style={{ color: 'var(--text-3)', fontSize: 12 }}>Target {usd(overview.readiness.target)}</div>
            </div>
            <div className="card">
              <div className="section-label mb-8">Retirement Share</div>
              <div className="num-mid">{overview.retirement_pct_of_net_worth.toFixed(1)}%</div>
              <div style={{ color: 'var(--text-3)', fontSize: 12 }}>of investable net worth</div>
            </div>
          </div>

          <div className="grid-2">
            <div className="card">
              <div className="section-label mb-12">Retirement Accounts</div>
              {overview.retirement_accounts.length === 0 && (
                <div className="empty-sub">No retirement accounts found yet.</div>
              )}
              {overview.retirement_accounts.map((a) => (
                <div key={a.id} className="flex-between" style={{ padding: '8px 0', borderBottom: '1px solid var(--border-soft)' }}>
                  <div>
                    <div>{a.name}</div>
                    <div style={{ color: 'var(--text-3)', fontSize: 12 }}>{a.type}</div>
                  </div>
                  <div className="num">{usd(a.balance)}</div>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="section-label mb-12">Contribution Utilization</div>
              {Object.entries(overview.contribution_utilization).map(([k, v]) => (
                <div key={k} style={{ marginBottom: 12 }}>
                  <div className="flex-between" style={{ fontSize: 13 }}>
                    <span style={{ textTransform: 'uppercase' }}>{k}</span>
                    <span>{v.utilization_pct.toFixed(1)}%</span>
                  </div>
                  <div style={{ height: 7, borderRadius: 999, background: 'var(--bg-elevated)', marginTop: 6 }}>
                    <div style={{ width: `${Math.min(100, v.utilization_pct)}%`, height: '100%', borderRadius: 999, background: 'var(--blue)' }} />
                  </div>
                  <div style={{ color: 'var(--text-3)', fontSize: 12, marginTop: 4 }}>
                    {usd(v.contributed)} / {usd(v.limit)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {tab === 'fire' && fire && (
        <>
          <div className="card mb-24">
            <div className="section-label mb-12">FIRE Type</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0,1fr))', gap: 8 }}>
              {(['lean', 'regular', 'fat', 'coast', 'barista'] as FireType[]).map((type) => (
                <button
                  key={type}
                  className="btn"
                  onClick={() => setFireType(type)}
                  style={{ borderColor: fireType === type ? 'var(--blue)' : 'var(--border)' }}
                >
                  {type.toUpperCase()}
                </button>
              ))}
            </div>
            {recommendation && (
              <div style={{ marginTop: 10, color: 'var(--text-2)', fontSize: 13 }}>
                Recommended: <strong>{recommendation.recommended_fire_type.toUpperCase()}</strong> — {recommendation.reason}
              </div>
            )}
          </div>

          <div className="card mb-24">
            <div className="retirement-controls-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Monthly contribution</label>
                <input type="number" value={monthlyContribution} onChange={(e) => setMonthlyContribution(Number(e.target.value))} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Expected return %</label>
                <input type="number" value={expectedReturn} step={0.1} onChange={(e) => setExpectedReturn(Number(e.target.value))} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Safe withdrawal %</label>
                <input type="number" value={swr} step={0.1} onChange={(e) => setSwr(Number(e.target.value))} />
              </div>
            </div>
          </div>

          <div className="grid-3 mb-24">
            <div className="card">
              <div className="section-label mb-8">FIRE Number</div>
              <div className="num-mid">{usd(fire.fire_number)}</div>
            </div>
            <div className="card">
              <div className="section-label mb-8">Progress</div>
              <div className="num-mid">{fire.progress_pct.toFixed(1)}%</div>
              <div style={{ color: 'var(--text-3)', fontSize: 12 }}>{usd(fire.current_balance)} current</div>
            </div>
            <div className="card">
              <div className="section-label mb-8">Time To FIRE</div>
              <div className="num-mid">{fire.time_to_fire_years ?? '100+'} years</div>
              <div style={{ color: 'var(--text-3)', fontSize: 12 }}>Savings rate {fire.savings_rate.toFixed(1)}%</div>
            </div>
          </div>

          <div className="card">
            <div className="section-label mb-10">Smart Nudges</div>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {fire.nudges.map((n, i) => (
                <li key={i} style={{ marginBottom: 6 }}>{n}</li>
              ))}
            </ul>
          </div>
        </>
      )}

      {tab === 'scenarios' && (
        <>
          <div className="card mb-24">
            <div className="retirement-controls-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16 }}>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Monthly add</label>
                <input type="number" value={scenarioContribution} onChange={(e) => setScenarioContribution(Number(e.target.value))} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Years</label>
                <input type="number" value={scenarioYears} onChange={(e) => setScenarioYears(Number(e.target.value))} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Conservative %</label>
                <input type="number" value={conservative} step={0.1} onChange={(e) => setConservative(Number(e.target.value))} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Moderate %</label>
                <input type="number" value={moderate} step={0.1} onChange={(e) => setModerate(Number(e.target.value))} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>Aggressive %</label>
                <input type="number" value={aggressive} step={0.1} onChange={(e) => setAggressive(Number(e.target.value))} />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="section-label mb-16">Scenario Curves</div>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={scenarioChartData}>
                <XAxis dataKey="year" tick={{ fill: 'var(--text-3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={compact} tick={{ fill: 'var(--text-3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Line type="monotone" dataKey="Conservative" stroke="#5cad7a" dot={false} />
                <Line type="monotone" dataKey="Moderate" stroke="#d4a840" dot={false} />
                <Line type="monotone" dataKey="Aggressive" stroke="#c95f52" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
