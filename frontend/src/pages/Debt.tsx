import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { DebtResponse, DebtAccount } from '../types'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, CartesianGrid,
} from 'recharts'

const TYPE_LABEL: Record<string, string> = {
  credit_card: 'Credit Card',
  student_loan: 'Student Loan',
  auto_loan: 'Auto Loan',
  personal_loan: 'Personal Loan',
}

const TYPE_COLOR: Record<string, string> = {
  credit_card: 'var(--neg)',
  student_loan: 'var(--text)',
  auto_loan: 'var(--accent)',
  personal_loan: 'var(--text-2)',
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtMonths(m: number | null) {
  if (m === null) return '∞'
  if (m < 12) return `${m}mo`
  const y = Math.floor(m / 12)
  const mo = m % 12
  return mo > 0 ? `${y}y ${mo}mo` : `${y}y`
}

interface EditState {
  interest_rate: string
  minimum_payment: string
}

export default function DebtPage() {
  const { data, loading, refetch } = useApi<DebtResponse>(() => api.get('/debt'), [])
  const [editing, setEditing] = useState<Record<number, EditState>>({})
  const [saving, setSaving] = useState<number | null>(null)

  const debts = data?.debts ?? []
  const summary = data?.summary

  function startEdit(d: DebtAccount) {
    setEditing(prev => ({
      ...prev,
      [d.account_id]: {
        interest_rate: String(d.interest_rate),
        minimum_payment: String(d.minimum_payment),
      },
    }))
  }

  async function saveEdit(accountId: number) {
    const e = editing[accountId]
    if (!e) return
    setSaving(accountId)
    await api.patch(`/debt/${accountId}`, {
      interest_rate: parseFloat(e.interest_rate) || 0,
      minimum_payment: parseFloat(e.minimum_payment) || 0,
    })
    setSaving(null)
    setEditing(prev => { const n = { ...prev }; delete n[accountId]; return n })
    refetch()
  }

  // Bar chart data
  const barData = debts.map(d => ({
    name: d.name.length > 16 ? d.name.slice(0, 14) + '…' : d.name,
    balance: d.balance,
    fill: TYPE_COLOR[d.type] ?? 'var(--text-3)',
  }))

  return (
    <div>
      <h1 className="page-title">Debt</h1>

      {loading ? (
        <div className="empty"><div className="empty-sub">Loading…</div></div>
      ) : debts.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">◌</div>
          <div className="empty-title">No debt accounts</div>
          <div className="empty-sub">Add Credit Card, Student Loan, Auto Loan, or Personal Loan accounts.</div>
        </div>
      ) : (
        <>
          {/* Summary stats */}
          {summary && (
            <div className="grid-4 mb-24">
              <div className="card stat-cell">
                <div className="lbl">Total Debt</div>
                <div className="val num-large" style={{ color: 'var(--neg)' }}>{fmt(summary.total_balance)}</div>
              </div>
              <div className="card stat-cell">
                <div className="lbl">Min Payments / mo</div>
                <div className="val num-mid num">{fmt(summary.total_minimum_payment)}</div>
              </div>
              <div className="card stat-cell">
                <div className="lbl">Highest APR</div>
                <div className="val num-mid num" style={{ color: summary.highest_rate > 15 ? 'var(--neg)' : 'var(--text)' }}>
                  {summary.highest_rate.toFixed(2)}%
                </div>
              </div>
              <div className="card stat-cell">
                <div className="lbl">Total Interest (minimums)</div>
                <div className="val num-mid num" style={{ color: 'var(--text-2)' }}>{fmt(summary.total_interest_if_minimums)}</div>
              </div>
            </div>
          )}

          <div className="grid-2 mb-24">
            {/* Balance by account */}
            <div className="card">
              <div className="section-label mb-16">Balance by Account</div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={barData} barCategoryGap="30%">
                  <XAxis dataKey="name" tick={{ fill: 'var(--text-3)', fontSize: 'var(--fs-xs)' }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fill: 'var(--text-3)', fontSize: 'var(--fs-xs)' }} axisLine={false} tickLine={false} width={52} />
                  <Tooltip
                    formatter={(v: number) => [fmt(v), 'Balance']}
                    contentStyle={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--r)', fontSize: 'var(--fs-sm)', fontFamily: 'var(--font-mono)' }}
                    labelStyle={{ color: 'var(--text-3)' }}
                  />
                  <Bar dataKey="balance" radius={[4, 4, 0, 0]}>
                    {barData.map((entry, i) => (
                      <rect key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Debt by type breakdown */}
            <div className="card">
              <div className="section-label mb-16">By Type</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-2)' }}>
                {Object.entries(
                  debts.reduce((acc, d) => {
                    acc[d.type] = (acc[d.type] ?? 0) + d.balance
                    return acc
                  }, {} as Record<string, number>)
                ).map(([type, bal]) => {
                  const pct = summary ? (bal / summary.total_balance) * 100 : 0
                  return (
                    <div key={type}>
                      <div className="flex-between mb-8">
                        <span style={{ fontSize: 'var(--fs-base)', color: TYPE_COLOR[type] ?? 'var(--text-2)' }}>
                          {TYPE_LABEL[type] ?? type}
                        </span>
                        <span className="num" style={{ fontSize: 'var(--fs-base)', color: 'var(--text)' }}>{fmt(bal)}</span>
                      </div>
                      <div style={{ height: 4, background: 'var(--bg-2)', borderRadius: 'var(--r-sm)' }}>
                        <div style={{ height: 4, width: `${pct}%`, background: TYPE_COLOR[type] ?? 'var(--text-3)', borderRadius: 'var(--r-sm)' }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Debt table */}
          <div className="card mb-24">
            <div className="section-label mb-16">Accounts</div>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Type</th>
                  <th style={{ textAlign: 'right' }}>Balance</th>
                  <th style={{ textAlign: 'right' }}>APR</th>
                  <th style={{ textAlign: 'right' }}>Min Payment</th>
                  <th style={{ textAlign: 'right' }}>Payoff</th>
                  <th style={{ textAlign: 'right' }}>Total Interest</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {debts.map(d => {
                  const e = editing[d.account_id]
                  return (
                    <tr key={d.account_id}>
                      <td>{d.name}</td>
                      <td>
                        <span className="tag" style={{ color: TYPE_COLOR[d.type] ?? 'var(--text-2)', borderColor: `${TYPE_COLOR[d.type] ?? '#7898b8'}30`, background: `${TYPE_COLOR[d.type] ?? '#7898b8'}0d` }}>
                          {TYPE_LABEL[d.type] ?? d.type}
                        </span>
                      </td>
                      <td className="num" style={{ textAlign: 'right', color: 'var(--neg)' }}>{fmt(d.balance)}</td>
                      <td style={{ textAlign: 'right' }}>
                        {e ? (
                          <input
                            value={e.interest_rate}
                            onChange={ev => setEditing(prev => ({ ...prev, [d.account_id]: { ...prev[d.account_id], interest_rate: ev.target.value } }))}
                            style={{ width: 60, textAlign: 'right', padding: '4px 8px', background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', color: 'var(--text)', fontSize: 'var(--fs-base)', fontFamily: 'var(--font-mono)', outline: 'none' }}
                          />
                        ) : (
                          <span className="num" style={{ color: d.interest_rate > 15 ? 'var(--neg)' : 'var(--text)' }}>
                            {d.interest_rate > 0 ? `${d.interest_rate.toFixed(2)}%` : '—'}
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {e ? (
                          <input
                            value={e.minimum_payment}
                            onChange={ev => setEditing(prev => ({ ...prev, [d.account_id]: { ...prev[d.account_id], minimum_payment: ev.target.value } }))}
                            style={{ width: 80, textAlign: 'right', padding: '4px 8px', background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', color: 'var(--text)', fontSize: 'var(--fs-base)', fontFamily: 'var(--font-mono)', outline: 'none' }}
                          />
                        ) : (
                          <span className="num">{d.minimum_payment > 0 ? fmt(d.minimum_payment) : '—'}</span>
                        )}
                      </td>
                      <td className="num" style={{ textAlign: 'right' }}>{fmtMonths(d.months_to_payoff)}</td>
                      <td className="num" style={{ textAlign: 'right', color: 'var(--text-2)' }}>
                        {d.total_interest !== null ? fmt(d.total_interest) : '—'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {e ? (
                          <div className="flex-end gap-8">
                            <button className="btn btn-sm btn-primary" onClick={() => saveEdit(d.account_id)} disabled={saving === d.account_id}>
                              {saving === d.account_id ? '…' : 'Save'}
                            </button>
                            <button className="btn btn-sm" onClick={() => setEditing(prev => { const n = { ...prev }; delete n[d.account_id]; return n })}>
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button className="btn btn-sm" onClick={() => startEdit(d)}>Edit</button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
