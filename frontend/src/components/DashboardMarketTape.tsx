import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import type {
  DashboardTape,
  DashboardTapeNewsItem,
  DashboardTapePersonalItem,
  DashboardTapeTickerItem,
  MarketTapeKind,
} from '../types'

type Props = {
  data: DashboardTape | null
  loading: boolean
  visible: boolean
}

type TapeEntry =
  | { kind: 'news'; id: string; item: DashboardTapeNewsItem }
  | { kind: 'ticker'; id: string; item: DashboardTapeTickerItem }
  | { kind: 'personal'; id: string; item: DashboardTapePersonalItem }

const EMPTY_TAPE: DashboardTape = {
  generated_at: '',
  segments: {
    news: [],
    tickers: [],
    personal: [],
  },
  sequence: [],
}

function formatPrice(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value)
}

function normalizeTape(data: DashboardTape | null): DashboardTape {
  if (!data || typeof data !== 'object') return EMPTY_TAPE
  const segments = data.segments ?? EMPTY_TAPE.segments
  return {
    generated_at: typeof data.generated_at === 'string' ? data.generated_at : '',
    segments: {
      news: Array.isArray(segments.news) ? segments.news : [],
      tickers: Array.isArray(segments.tickers) ? segments.tickers : [],
      personal: Array.isArray(segments.personal) ? segments.personal : [],
    },
    sequence: Array.isArray(data.sequence) ? data.sequence : [],
  }
}

function buildEntries(data: DashboardTape): TapeEntry[] {
  const newsById = new Map(data.segments.news.map((item) => [item.id, item]))
  const tickerById = new Map(data.segments.tickers.map((item) => [item.id, item]))
  const personalById = new Map(data.segments.personal.map((item) => [item.id, item]))

  const fallbackSequence = [
    ...data.segments.news.map((item) => ({ kind: 'news' as const, ref_id: item.id })),
    ...data.segments.tickers.map((item) => ({ kind: 'ticker' as const, ref_id: item.id })),
    ...data.segments.personal.map((item) => ({ kind: 'personal' as const, ref_id: item.id })),
  ]
  const sourceSequence = data.sequence.length > 0 ? data.sequence : fallbackSequence

  const entries: TapeEntry[] = []
  for (const block of sourceSequence) {
    const kind = block.kind as MarketTapeKind
    if (kind === 'news') {
      const item = newsById.get(block.ref_id)
      if (item) entries.push({ kind: 'news', id: `${block.ref_id}-${entries.length}`, item })
      continue
    }
    if (kind === 'ticker') {
      const item = tickerById.get(block.ref_id)
      if (item) entries.push({ kind: 'ticker', id: `${block.ref_id}-${entries.length}`, item })
      continue
    }
    if (kind === 'personal') {
      const item = personalById.get(block.ref_id)
      if (item) entries.push({ kind: 'personal', id: `${block.ref_id}-${entries.length}`, item })
    }
  }

  // Guard against malformed sequence IDs by rendering directly from available segments.
  if (entries.length > 0) return entries
  return [
    ...data.segments.news.map((item, idx) => ({ kind: 'news' as const, id: `${item.id}-fallback-${idx}`, item })),
    ...data.segments.tickers.map((item, idx) => ({ kind: 'ticker' as const, id: `${item.id}-fallback-${idx}`, item })),
    ...data.segments.personal.map((item, idx) => ({ kind: 'personal' as const, id: `${item.id}-fallback-${idx}`, item })),
  ]
}

function TapeRun({ entries, onNavigate, clone = false }: { entries: TapeEntry[]; onNavigate: (route: '/accounts' | '/insights') => void; clone?: boolean }) {
  return (
    <div className={`dashboard-market-tape-run${clone ? ' is-clone' : ''}`} aria-hidden={clone}>
      {entries.map((entry) => {
        if (entry.kind === 'news') {
          return (
            <span key={entry.id} className="dashboard-market-tape-token news" data-testid="market-tape-item-news">
              <span className="dashboard-market-tape-tag">NEWS</span>
              <a
                href={entry.item.url}
                target="_blank"
                rel="noreferrer"
                className="dashboard-market-tape-link"
                data-testid="market-tape-news-link"
              >
                {entry.item.label}
              </a>
              {entry.item.source ? <span className="dashboard-market-tape-meta">{entry.item.source}</span> : null}
            </span>
          )
        }

        if (entry.kind === 'ticker') {
          return (
            <span key={entry.id} className="dashboard-market-tape-token ticker" data-testid="market-tape-item-ticker">
              <span className="dashboard-market-tape-tag">TICKER</span>
              <button
                type="button"
                className="dashboard-market-tape-btn"
                onClick={() => onNavigate('/accounts')}
              >
                <span className="dashboard-market-tape-symbol">{entry.item.symbol}</span>
                <span className="dashboard-market-tape-meta">{formatPrice(entry.item.price)}</span>
                <span className="dashboard-market-tape-meta">{entry.item.portfolio_weight_pct.toFixed(1)}%</span>
              </button>
            </span>
          )
        }

        return (
          <span
            key={entry.id}
            className={`dashboard-market-tape-token personal tone-${entry.item.tone}`}
            data-testid="market-tape-item-personal"
          >
            <span className="dashboard-market-tape-tag">SIGNAL</span>
            <button
              type="button"
              className="dashboard-market-tape-btn"
              onClick={() => onNavigate(entry.item.route)}
            >
              {entry.item.label}
            </button>
          </span>
        )
      })}
    </div>
  )
}

export default function DashboardMarketTape({ data, loading, visible }: Props) {
  const navigate = useNavigate()
  const [reduceMotion, setReduceMotion] = useState(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })
  const normalized = useMemo(() => normalizeTape(data), [data])
  const entries = useMemo(() => buildEntries(normalized), [normalized])
  const durationSeconds = Math.max(34, entries.length * 4.5)
  const trackStyle = { '--tape-duration': `${durationSeconds}s` } as CSSProperties

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const sync = () => setReduceMotion(media.matches)
    sync()
    if ('addEventListener' in media) {
      media.addEventListener('change', sync)
      return () => media.removeEventListener('change', sync)
    }
    const legacyMedia = media as MediaQueryList & {
      addListener?: (listener: () => void) => void
      removeListener?: (listener: () => void) => void
    }
    legacyMedia.addListener?.(sync)
    return () => legacyMedia.removeListener?.(sync)
  }, [])

  if (!visible) return null

  if (entries.length === 0 && loading) {
    return (
      <div className="dashboard-market-tape" data-testid="dashboard-market-tape">
        <div className="dashboard-market-tape-status">Loading live tape…</div>
      </div>
    )
  }

  if (entries.length === 0) {
    return (
      <div className="dashboard-market-tape" data-testid="dashboard-market-tape">
        <div className="dashboard-market-tape-status">Live tape is warming up with your latest signals.</div>
      </div>
    )
  }

  return (
    <div className="dashboard-market-tape" data-testid="dashboard-market-tape">
      <div className={`dashboard-market-tape-viewport${reduceMotion ? ' is-reduced-motion' : ''}`}>
        <div
          className={`dashboard-market-tape-track${reduceMotion ? ' is-reduced-motion' : ''}`}
          style={trackStyle}
        >
          <TapeRun entries={entries} onNavigate={(route) => navigate(route)} />
          {!reduceMotion ? <TapeRun entries={entries} onNavigate={(route) => navigate(route)} clone /> : null}
        </div>
      </div>
    </div>
  )
}
