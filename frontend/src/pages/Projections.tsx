import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Projection } from '../types'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'

function formatUsd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

export default function Projections() {
  const [contribution, setContribution] = useState(1000)
  const [years, setYears] = useState(10)
  const [conservative, setConservative] = useState(4)
  const [moderate, setModerate] = useState(7)
  const [aggressive, setAggressive] = useState(10)

  const params = `?monthly_contribution=${contribution}&years=${years}&conservative_rate=${conservative / 100}&moderate_rate=${moderate / 100}&aggressive_rate=${aggressive / 100}`
  const { data } = useApi<Projection>(() => api.get(`/projections${params}`), [contribution, years, conservative, moderate, aggressive])

  const chartData = data
    ? data.scenarios.conservative.map((_, i) => ({
        year: i,
        conservative: data.scenarios.conservative[i].value,
        moderate: data.scenarios.moderate[i].value,
        aggressive: data.scenarios.aggressive[i].value,
      }))
    : []

  return (
    <div>
      <h1 className="page-title">Projections</h1>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16 }}>
          <div className="form-group">
            <label>Monthly Contribution ($)</label>
            <input type="number" value={contribution} onChange={(e) => setContribution(Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Time Horizon (years)</label>
            <input type="number" value={years} onChange={(e) => setYears(Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Conservative (%)</label>
            <input type="number" value={conservative} onChange={(e) => setConservative(Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Moderate (%)</label>
            <input type="number" value={moderate} onChange={(e) => setModerate(Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Aggressive (%)</label>
            <input type="number" value={aggressive} onChange={(e) => setAggressive(Number(e.target.value))} />
          </div>
        </div>
      </div>

      {data && (
        <div className="stat-card" style={{ marginBottom: 20, display: 'inline-block' }}>
          <div className="label">Current Portfolio Value</div>
          <div className="value">{formatUsd(data.current_balance)}</div>
        </div>
      )}

      <div className="card">
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Projected Growth</h3>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <XAxis dataKey="year" tick={{ fill: '#8888a0', fontSize: 12 }} label={{ value: 'Years', position: 'bottom', fill: '#8888a0' }} />
              <YAxis tick={{ fill: '#8888a0', fontSize: 12 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ background: '#1a1a26', border: '1px solid #1f1f2e', borderRadius: 8 }}
                formatter={(v: number, name: string) => [formatUsd(v), name]}
              />
              <Legend />
              <Line type="monotone" dataKey="conservative" stroke="#06b6d4" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="moderate" stroke="#6366f1" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="aggressive" stroke="#22c55e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">Configure parameters above to see projections</div>
        )}
      </div>

      {data && (
        <div style={{ marginTop: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Projected Values at Year {years}</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            {(['conservative', 'moderate', 'aggressive'] as const).map((scenario) => {
              const final = data.scenarios[scenario][data.scenarios[scenario].length - 1]
              return (
                <div key={scenario} className="stat-card">
                  <div className="label">{scenario} ({scenario === 'conservative' ? conservative : scenario === 'moderate' ? moderate : aggressive}%)</div>
                  <div className="value" style={{ fontSize: 24 }}>{formatUsd(final.value)}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
