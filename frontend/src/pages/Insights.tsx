import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Insight } from '../types'

export default function InsightsPage() {
  const { data: insights, loading } = useApi<Insight[]>(() => api.get('/insights'), [])

  return (
    <div>
      <h1 className="page-title">Insights</h1>

      {loading ? (
        <div className="empty-state">Loading insights...</div>
      ) : insights && insights.length > 0 ? (
        <div className="card-grid">
          {insights.map((insight, i) => (
            <div key={i} className="insight-card">
              <div className={`insight-category cat-${insight.category}`}>
                {insight.category}
              </div>
              <div className="insight-title">{insight.title}</div>
              <div className="insight-desc">{insight.description}</div>
              <div className="insight-why">{insight.why}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          No insights yet. Import account data and refresh prices to generate insights.
        </div>
      )}
    </div>
  )
}
