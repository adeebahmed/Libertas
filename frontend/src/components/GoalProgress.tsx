import { useMemo } from 'react'
import type { RetirementPlan } from '../types'

function usd(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

export default function GoalProgress({
  plan,
  fireType,
}: {
  plan: RetirementPlan | null
  fireType: string
}) {
  const progress = useMemo(() => {
    if (!plan || !plan.target) return 0
    return Math.max(0, Math.min(100, (plan.current_balance / plan.target) * 100))
  }, [plan])

  if (!plan) return null

  const nudges: string[] = []
  if (plan.needed_monthly_contribution && plan.needed_monthly_contribution > plan.monthly_contribution) {
    const delta = plan.needed_monthly_contribution - plan.monthly_contribution
    nudges.push(`Increase contribution by ${usd(delta)}/mo to stay on timeline.`)
  }
  if (plan.on_track?.on_track) {
    nudges.push('You are currently on track. Keep contribution consistency high.')
  }
  if (plan.years_to_target && plan.years_to_target <= 10) {
    nudges.push(`At current pace, target in about ${plan.years_to_target} years.`)
  }
  if (!nudges.length) {
    nudges.push('Set monthly contribution in Settings to generate stronger trajectory guidance.')
  }

  return (
    <div className="card mb-24">
      <div className="flex-between mb-12">
        <div>
          <div className="section-label mb-4">FIRE Goal Progress</div>
          <div style={{ color: 'var(--text-2)', fontSize: 13 }}>
            Mode: <strong style={{ textTransform: 'uppercase' }}>{fireType || 'regular'}</strong>
          </div>
        </div>
        <div className="num" style={{ fontSize: 18 }}>{progress.toFixed(1)}%</div>
      </div>

      <div style={{ height: 8, borderRadius: 999, background: 'var(--bg-elevated)', marginBottom: 10 }}>
        <div style={{ width: `${progress}%`, height: '100%', borderRadius: 999, background: 'var(--blue)' }} />
      </div>

      <div className="grid-3 mb-12">
        <div>
          <div className="section-label mb-4">Current</div>
          <div className="num-mid">{usd(plan.current_balance)}</div>
        </div>
        <div>
          <div className="section-label mb-4">Target</div>
          <div className="num-mid">{usd(plan.target)}</div>
        </div>
        <div>
          <div className="section-label mb-4">Timeline</div>
          <div className="num-mid">{plan.years_to_target ?? '100+'} years</div>
        </div>
      </div>

      <ul style={{ margin: 0, paddingLeft: 18 }}>
        {nudges.map((n, i) => (
          <li key={i} style={{ marginBottom: 5, color: 'var(--text-2)' }}>{n}</li>
        ))}
      </ul>
    </div>
  )
}
