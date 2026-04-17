import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { TaxEstimate, TaxHarvestOpportunity } from '../types'

function usd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function pct(n: number) {
  return `${n.toFixed(1)}%`
}

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="card stat-cell">
      <div className="lbl">{label}</div>
      <div className="val num-mid num" style={{ color: color ?? 'var(--text)' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

export default function TaxesPage() {
  const { data: estimate, loading: estLoading } = useApi<TaxEstimate>(() => api.get('/taxes/estimate'), [])
  const { data: harvest } = useApi<{ opportunities: TaxHarvestOpportunity[]; total_harvestable_loss: number; estimated_tax_savings: number; note: string }>(() => api.get('/taxes/harvesting'), [])
  const { data: recs } = useApi<{ recommendations: { type: string; priority: string; reason: string; limit_2024: number }[]; total_income: number; filing_status: string }>(() => api.get('/taxes/entity-recommendations'), [])

  const noIncome = estimate && estimate.total_income === 0

  return (
    <div>
      <h1 className="page-title">Taxes</h1>

      {noIncome && (
        <div className="card mb-24" style={{ borderColor: 'var(--accent-dim)', background: 'rgba(201,169,110,0.05)' }}>
          <div style={{ fontSize: 13, color: 'var(--text-2)' }}>
            Add your income in <a href="/settings" style={{ color: 'var(--accent)' }}>Settings</a> to see your tax estimate. Go to Settings → Income &amp; Tax.
          </div>
        </div>
      )}

      {/* Tax estimate */}
      <div className="section-label mb-16">2024 Tax Estimate</div>
      {estLoading ? (
        <div className="empty"><div className="empty-sub">Calculating…</div></div>
      ) : estimate && (
        <>
          <div className="grid-4 mb-24">
            <StatCard label="Total Income" value={usd(estimate.total_income)} />
            <StatCard label="AGI" value={usd(estimate.agi)} sub={`−${usd(estimate.standard_deduction)} std deduction`} />
            <StatCard label="Taxable Income" value={usd(estimate.taxable_income)} />
            <StatCard label="Effective Rate" value={pct(estimate.effective_rate)} color={estimate.effective_rate > 30 ? 'var(--neg)' : 'var(--text)'} />
          </div>

          <div className="card mb-32" style={{ padding: 0 }}>
            <table className="tbl">
              <thead>
                <tr><th>Component</th><th style={{ textAlign: 'right' }}>Amount</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>Ordinary income tax</td>
                  <td className="num" style={{ textAlign: 'right' }}>{usd(estimate.ordinary_tax)}</td>
                </tr>
                {estimate.self_employment_tax > 0 && (
                  <tr>
                    <td>Self-employment tax (15.3%)</td>
                    <td className="num" style={{ textAlign: 'right' }}>{usd(estimate.self_employment_tax)}</td>
                  </tr>
                )}
                {estimate.net_capital_gains > 0 && (
                  <tr>
                    <td>Long-term capital gains tax</td>
                    <td className="num" style={{ textAlign: 'right' }}>{usd(estimate.ltcg_tax)}</td>
                  </tr>
                )}
                <tr style={{ fontWeight: 600 }}>
                  <td>Total estimated tax</td>
                  <td className="num" style={{ textAlign: 'right', color: 'var(--neg)' }}>{usd(estimate.total_estimated_tax)}</td>
                </tr>
                <tr>
                  <td style={{ color: 'var(--text-2)' }}>Quarterly payment (est.)</td>
                  <td className="num" style={{ textAlign: 'right', color: 'var(--text-2)' }}>{usd(estimate.quarterly_payment)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Tax-loss harvesting */}
      <div className="section-label mb-16">Tax-Loss Harvesting</div>
      {harvest && (
        <div className="mb-32">
          {harvest.opportunities.length > 0 ? (
            <>
              <div className="grid-2 mb-16">
                <StatCard
                  label="Harvestable Losses"
                  value={usd(harvest.total_harvestable_loss)}
                  color="var(--neg)"
                />
                <StatCard
                  label="Est. Tax Savings"
                  value={usd(harvest.estimated_tax_savings)}
                  color="var(--pos)"
                />
              </div>
              <div className="card" style={{ padding: 0 }}>
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Account</th>
                      <th style={{ textAlign: 'right' }}>Shares</th>
                      <th style={{ textAlign: 'right' }}>Cost Basis</th>
                      <th style={{ textAlign: 'right' }}>Market Value</th>
                      <th style={{ textAlign: 'right' }}>Unrealized Loss</th>
                      <th style={{ textAlign: 'right' }}>Loss %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {harvest.opportunities.map(o => (
                      <tr key={`${o.symbol}-${o.account}`}>
                        <td style={{ fontWeight: 500 }}>{o.symbol}</td>
                        <td style={{ color: 'var(--text-2)' }}>{o.account}</td>
                        <td className="num" style={{ textAlign: 'right' }}>{o.quantity.toFixed(4)}</td>
                        <td className="num" style={{ textAlign: 'right' }}>{usd(o.cost_basis)}</td>
                        <td className="num" style={{ textAlign: 'right' }}>{usd(o.market_value)}</td>
                        <td className="num" style={{ textAlign: 'right', color: 'var(--neg)' }}>{usd(o.unrealized_loss)}</td>
                        <td className="num" style={{ textAlign: 'right', color: 'var(--neg)' }}>{o.loss_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-3)' }}>{harvest.note}</div>
            </>
          ) : (
            <div className="card">
              <div style={{ fontSize: 13, color: 'var(--text-2)' }}>No significant tax-loss harvesting opportunities in your taxable accounts right now.</div>
            </div>
          )}
        </div>
      )}

      {/* Account recommendations */}
      <div className="section-label mb-16">Account Recommendations</div>
      {recs && recs.recommendations.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {recs.recommendations.map(r => (
            <div key={r.type} className="card" style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{r.type}</span>
                  <span style={{
                    fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.4px',
                    color: r.priority === 'high' ? 'var(--neg)' : r.priority === 'medium' ? 'var(--accent)' : 'var(--text-3)',
                  }}>{r.priority}</span>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.55 }}>{r.reason}</div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 2 }}>2024 limit</div>
                <div className="num" style={{ fontSize: 14 }}>{usd(r.limit_2024)}</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">
          <div className="empty-sub">Add income in Settings to see personalized account recommendations.</div>
        </div>
      )}
    </div>
  )
}
