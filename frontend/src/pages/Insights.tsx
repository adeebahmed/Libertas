import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, Insight } from '../types'

const INSTITUTION_LINKS: Array<{ match: RegExp; label: string; url: string; types: string[] }> = [
  { match: /fidelity/i, label: 'Open Fidelity', url: 'https://digital.fidelity.com/ftgw/digital/transfer/', types: ['401k', 'roth_ira', 'brokerage', 'hsa'] },
  { match: /schwab/i, label: 'Open Schwab', url: 'https://client.schwab.com/', types: ['401k', 'roth_ira', 'brokerage'] },
  { match: /vanguard/i, label: 'Open Vanguard', url: 'https://investor.vanguard.com/my-account', types: ['401k', 'roth_ira', 'brokerage'] },
  { match: /robinhood/i, label: 'Open Robinhood', url: 'https://robinhood.com/', types: ['brokerage', 'crypto'] },
  { match: /coinbase/i, label: 'Open Coinbase', url: 'https://coinbase.com/', types: ['crypto'] },
  { match: /chase/i, label: 'Open Chase', url: 'https://secure.chase.com/', types: ['checking', 'savings', 'credit_card'] },
  { match: /bank of america/i, label: 'Open BofA', url: 'https://bankofamerica.com/', types: ['checking', 'savings', 'credit_card'] },
  { match: /wells fargo/i, label: 'Open Wells Fargo', url: 'https://wellsfargo.com/', types: ['checking', 'savings', 'credit_card', 'mortgage'] },
  { match: /ally/i, label: 'Open Ally', url: 'https://ally.com/', types: ['checking', 'savings'] },
  { match: /marcus/i, label: 'Open Marcus', url: 'https://marcus.com/', types: ['savings'] },
]

const HINT_ACCOUNT_TYPES: Record<string, string[]> = {
  savings: ['savings'],
  checking: ['checking'],
  brokerage: ['brokerage'],
  '401k': ['401k', 'roth_ira'],
  mortgage: ['real_estate'],
  credit_card: ['credit_card'],
  crypto: ['crypto'],
}

const ICONS: Record<string, string> = {
  shield: '🛡',
  umbrella: '☂',
  pie: '◔',
  credit: '💳',
  grid: '▦',
  trending: '↗',
  flag: '⚑',
  piggy: '◈',
  chart: '⬡',
  clock: '◷',
  percent: '%',
  house: '⌂',
  wallet: '▣',
  pulse: '∿',
  leaf: '◉',
  sparkle: '✦',
}

function getActionLink(insight: Insight, accounts: Account[] | null | undefined) {
  if (!insight.institution_hint || !accounts) return null
  const relevantTypes = HINT_ACCOUNT_TYPES[insight.institution_hint] ?? []
  const matching = accounts.filter(a => relevantTypes.includes(a.type))
  for (const account of matching) {
    const name = account.institution_name ?? ''
    const link = INSTITUTION_LINKS.find(l => l.match.test(name) && l.types.some(t => relevantTypes.includes(t)))
    if (link) return link
  }
  return null
}

export default function InsightsPage() {
  const { data: insights, loading, refetch } = useApi<Insight[]>(() => api.get('/insights'), [])
  const { data: accounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const [filter, setFilter] = useState<'attention' | 'good'>('attention')

  const filtered = insights?.filter(i =>
    filter === 'attention' ? (i.priority === 'high' || i.priority === 'medium') : i.priority === 'low'
  ) ?? []

  const attentionCount = insights?.filter(i => i.priority === 'high' || i.priority === 'medium').length ?? 0
  const goodCount = insights?.filter(i => i.priority === 'low').length ?? 0

  return (
    <div>
      <h1 className="page-title" style={{ marginBottom: 6 }}>Insights</h1>

      <div className="insights-filter-row">
        <button
          onClick={() => setFilter('attention')}
          className={`insight-filter-btn${filter === 'attention' ? ' active attention' : ''}`}
        >
          <span>Needs attention</span>
          <span className="insight-filter-count">{attentionCount}</span>
        </button>
        <button
          onClick={() => setFilter('good')}
          className={`insight-filter-btn${filter === 'good' ? ' active good' : ''}`}
        >
          <span>Looking good</span>
          <span className="insight-filter-count">{goodCount}</span>
        </button>
      </div>

      {loading ? (
        <div className="empty"><div className="empty-sub">Analysing portfolio...</div></div>
      ) : filtered.length > 0 ? (
        <div className="grid-auto">
          {filtered
            .sort((a, b) => {
              const order = { high: 0, medium: 1, low: 2 }
              return (order[a.priority] ?? 3) - (order[b.priority] ?? 3)
            })
            .map((ins, i) => {
              const quickLink = getActionLink(ins, accounts)
              const icon = ICONS[ins.icon ?? ''] ?? null
              return (
                <div key={i} className={`insight-card insight-${ins.priority}`}>
                  <div className="insight-header">
                    {icon && <span className="insight-icon">{icon}</span>}
                    <div className="insight-title">{ins.title}</div>
                    <span className={`insight-status-dot insight-dot-${ins.priority}`} />
                  </div>
                  <div className="insight-desc">{ins.description}</div>
                  <div className="insight-footer">
                    {quickLink ? (
                      <a
                        className="insight-cta-btn insight-cta-link"
                        href={quickLink.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {ins.action}
                        <span className="insight-link-chip">{quickLink.label} ↗</span>
                      </a>
                    ) : (
                      <div className="insight-cta-btn">{ins.action}</div>
                    )}
                  </div>
                </div>
              )
            })}
        </div>
      ) : (
        <div className="empty">
          <div className="empty-icon">◌</div>
          <div className="empty-title">
            {filter === 'attention' ? 'Nothing needs attention right now' : 'No on-track items yet'}
          </div>
          <div className="empty-sub">Import account data and refresh prices to generate insights</div>
        </div>
      )}

      <div className="mt-24">
        <button className="btn btn-ghost" onClick={refetch}>Refresh Insights</button>
      </div>
    </div>
  )
}
