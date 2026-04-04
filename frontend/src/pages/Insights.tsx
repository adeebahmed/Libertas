import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Insight } from '../types'

const CAT_CLASS: Record<string, string> = {
  Risk: 'risk', Performance: 'perf', Allocation: 'alloc',
  Liquidity: 'liquid', Trends: 'trend', Retirement: 'retirement',
  Debt: 'debt', Tax: 'tax', Behavioral: 'behavioral', Estate: 'estate',
  info: 'info',
}

export default function InsightsPage() {
  const { data: insights, loading, refetch } = useApi<Insight[]>(() => api.get('/insights'), [])

  return (
    <div>
      <div className="flex-between mb-32">
        <h1 className="page-title" style={{ marginBottom: 0 }}>Insights</h1>
        <button className="btn" onClick={refetch}>Refresh</button>
      </div>

      {loading ? (
        <div className="empty"><div className="empty-sub">Analysing portfolio…</div></div>
      ) : insights && insights.length > 0 ? (
        <div className="grid-auto">
          {insights.map((ins, i) => {
            const cls = CAT_CLASS[ins.category] ?? 'info'
            return (
              <div key={i} className={`insight-card ${cls}`}>
                <div className="insight-cat">{ins.category}</div>
                <div className="insight-title">{ins.title}</div>
                <div className="insight-desc">{ins.description}</div>
                <div className="insight-why">{ins.why}</div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="empty">
          <div className="empty-icon">◌</div>
          <div className="empty-title">No insights yet</div>
          <div className="empty-sub">Import account data and refresh prices to generate insights</div>
        </div>
      )}
    </div>
  )
}
