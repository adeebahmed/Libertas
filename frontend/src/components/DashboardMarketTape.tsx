import { useEffect, useMemo, useRef, useState } from 'react'
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
  | { kind: 'pair'; id: string; ticker: DashboardTapeTickerItem; news: DashboardTapeNewsItem; pairTone: number | null }
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

function performanceEmoji(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '➖'
  if (value > 0.1) return '📈'
  if (value < -0.1) return '📉'
  return '➖'
}

function performanceDirection(value: number | null | undefined): 'up' | 'down' | 'flat' {
  if (value == null || Number.isNaN(value)) return 'flat'
  if (value > 0.01) return 'up'
  if (value < -0.01) return 'down'
  return 'flat'
}

function formatPercent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
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
  let pairIndex = 0
  for (let i = 0; i < sourceSequence.length; i += 1) {
    const block = sourceSequence[i]
    const kind = block.kind as MarketTapeKind
    if (kind === 'ticker') {
      const next = sourceSequence[i + 1]
      if (next && (next.kind as MarketTapeKind) === 'news') {
        const ticker = tickerById.get(block.ref_id)
        const news = newsById.get(next.ref_id)
        if (ticker && news) {
          entries.push({
            kind: 'pair',
            id: `${block.ref_id}-${next.ref_id}-${entries.length}`,
            ticker,
            news,
            pairTone: pairIndex % 6,
          })
          pairIndex += 1
          i += 1
          continue
        }
      }
    }
    if (kind === 'personal') {
      const item = personalById.get(block.ref_id)
      if (item) entries.push({ kind: 'personal', id: `${block.ref_id}-${entries.length}`, item })
    }
  }

  // Guard against malformed sequence IDs by rendering directly from available segments.
  if (entries.length > 0) return entries
  const fallbackPairs = data.segments.tickers
    .slice(0, data.segments.news.length)
    .map((ticker, idx) => ({
      kind: 'pair' as const,
      id: `${ticker.id}-${data.segments.news[idx].id}-fallback-${idx}`,
      ticker,
      news: data.segments.news[idx],
      pairTone: idx % 6,
    }))
  return [
    ...fallbackPairs,
    ...data.segments.personal.map((item, idx) => ({ kind: 'personal' as const, id: `${item.id}-fallback-${idx}`, item })),
  ]
}

function TapeRun({ entries, onNavigate, clone = false }: { entries: TapeEntry[]; onNavigate: (route: '/accounts' | '/insights') => void; clone?: boolean }) {
  return (
    <div className={`dashboard-market-tape-run${clone ? ' is-clone' : ''}`} aria-hidden={clone}>
      {entries.map((entry) => {
        if (entry.kind === 'pair') {
          const pairClass = entry.pairTone != null ? ` pair-tone-${entry.pairTone}` : ''
          const emoji = performanceEmoji(entry.ticker.performance_pct)
          const moveClass = performanceDirection(entry.ticker.performance_pct)
          const changeText = formatPercent(entry.ticker.performance_pct)
          return (
            <span key={entry.id} className={`dashboard-market-tape-token news${pairClass}`} data-testid="market-tape-item-news">
              <a
                href={entry.news.url}
                target="_blank"
                rel="noreferrer"
                className="dashboard-market-tape-link"
                data-testid="market-tape-news-link"
              >
                <span>{emoji}</span>
                <span className="dashboard-market-tape-ticker-strong">
                  <span className="dashboard-market-tape-ticker-symbol">{entry.ticker.symbol}</span>
                  <span className={`dashboard-market-tape-ticker-price is-${moveClass}`}>{formatPrice(entry.ticker.price)}</span>
                  {changeText !== '—' ? (
                    <span className={`dashboard-market-tape-ticker-change is-${moveClass}`}>{changeText}</span>
                  ) : null}
                </span>
                <span>-</span>
                <span>{entry.news.label}</span>
              </a>
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
  const [speedUp, setSpeedUp] = useState(false)
  const trackRef = useRef<HTMLDivElement>(null)
  const durationSeconds = Math.max(82, entries.length * 9.8)
  const trackStyle = { '--tape-duration': `${durationSeconds}s` } as CSSProperties
  // Keep duration accessible in rAF loop without re-creating the effect
  const durationRef = useRef(durationSeconds)
  durationRef.current = durationSeconds

  const animRef = useRef({ offset: 0, speed: 1, targetSpeed: 1, lastTime: 0, rafId: 0 })

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

  // rAF-driven scroll — replaces CSS animation so speed lerps smoothly.
  // Depends on entries.length so it (re)starts once the track DOM node is mounted.
  useEffect(() => {
    if (reduceMotion) return
    const track = trackRef.current
    if (!track) return

    const state = animRef.current
    cancelAnimationFrame(state.rafId)
    track.style.animation = 'none'
    if (state.offset === 0) state.speed = 1
    state.lastTime = performance.now()

    const tick = (now: number) => {
      const dt = Math.min((now - state.lastTime) / 1000, 0.05)
      state.lastTime = now
      const el = trackRef.current
      if (el) {
        const contentWidth = el.scrollWidth / 2
        if (contentWidth > 0) {
          state.speed += (state.targetSpeed - state.speed) * 0.08
          state.offset -= (contentWidth / durationRef.current) * dt * state.speed
          if (state.offset <= -contentWidth) state.offset += contentWidth
          el.style.transform = `translateX(${state.offset}px)`
        }
      }
      state.rafId = requestAnimationFrame(tick)
    }
    state.rafId = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(state.rafId)
    }
  }, [reduceMotion, entries.length])

  // Key handlers — toggle speed on ArrowRight, reset on blur
  useEffect(() => {
    if (reduceMotion) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'ArrowRight' || e.repeat) return
      const next = animRef.current.targetSpeed === 1 ? 3 : 1
      animRef.current.targetSpeed = next
      setSpeedUp(next === 3)
    }
    const onBlur = () => {
      animRef.current.targetSpeed = 1
      setSpeedUp(false)
    }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('blur', onBlur)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('blur', onBlur)
    }
  }, [reduceMotion])

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
      <div
        className={`dashboard-market-tape-viewport${reduceMotion ? ' is-reduced-motion' : ''}${speedUp ? ' is-fast' : ''}`}
      >
        <div
          ref={trackRef}
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
