import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Projection } from '../types'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

function usd(n: number) {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}k`
  return `$${n.toFixed(0)}`
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#1c1a14', border: '1px solid #26231b', borderRadius: 8, padding: '10px 14px', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
      <div style={{ color: '#5c5444', marginBottom: 6 }}>Year {label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color, marginBottom: 2 }}>
          {p.name}: {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(p.value)}
        </div>
      ))}
    </div>
  )
}

export default function Projections() {
  const [contribution, setContribution] = useState(2000)
  const [years, setYears] = useState(20)
  const [conservative, setConservative] = useState(4)
  const [moderate, setModerate] = useState(7)
  const [aggressive, setAggressive] = useState(10)

  const qs = `?monthly_contribution=${contribution}&years=${years}&conservative_rate=${conservative / 100}&moderate_rate=${moderate / 100}&aggressive_rate=${aggressive / 100}`
  const { data } = useApi<Projection>(() => api.get(`/projections${qs}`), [contribution, years, conservative, moderate, aggressive])

  const chartData = data
    ? data.scenarios.conservative.map((_, i) => ({
        year: i,
        Conservative: data.scenarios.conservative[i].value,
        Moderate: data.scenarios.moderate[i].value,
        Aggressive: data.scenarios.aggressive[i].value,
      }))
    : []

  const last = (arr: { value: number }[]) => arr[arr.length - 1]?.value ?? 0
  const finals = data ? {
    conservative: last(data.scenarios.conservative),
    moderate:     last(data.scenarios.moderate),
    aggressive:   last(data.scenarios.aggressive),
  } : null

  return (
    <div>
      <h1 className="page-title">Projections</h1>

      {/* Parameters */}
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
              <input type="number" value={value} step={step}
                onChange={(e) => set(Number(e.target.value))} />
            </div>
          ))}
        </div>
      </div>

      {/* Terminal values */}
      {finals && data && (
        <div className="grid-3 mb-24">
          {([['Conservative', finals.conservative, '#5cad7a', conservative],
             ['Moderate',     finals.moderate,     '#c9a96e', moderate],
             ['Aggressive',   finals.aggressive,   '#c95f52', aggressive]] as const).map(([name, val, color, rate]) => (
            <div key={name} className="card" style={{ borderTop: `3px solid ${color}`, paddingTop: 18 }}>
              <div className="section-label mb-8">{name} · {rate}% / yr</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 26, letterSpacing: -0.5, color: 'var(--text)', marginBottom: 6 }}>
                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val as number)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                in {years} yrs from {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(data.current_balance)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="card">
        <div className="section-label mb-16">Growth scenarios</div>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, left: -4, bottom: 0 }}>
              <XAxis dataKey="year" tick={{ fill: '#5c5444', fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: 'years', position: 'insideBottomRight', offset: 0, fill: '#5c5444', fontSize: 11 }} />
              <YAxis tick={{ fill: '#5c5444', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={usd} />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine x={0} stroke="#26231b" />
              <Line type="monotone" dataKey="Conservative" stroke="#5cad7a" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="Moderate"     stroke="#c9a96e" strokeWidth={2}   dot={false} />
              <Line type="monotone" dataKey="Aggressive"   stroke="#c95f52" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty">
            <div className="empty-sub">Adjust parameters above</div>
          </div>
        )}
      </div>
    </div>
  )
}
