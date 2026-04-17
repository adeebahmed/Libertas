import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useChordHotkeys, useCommandPaletteHotkeys } from '../hooks/useHotkeys'

type Command = {
  id: string
  title: string
  meta: string
  shortcut?: string
  run: () => void
}

const PAGE_COMMANDS = [
  { title: 'Dashboard', path: '/', shortcut: 'g d' },
  { title: 'Accounts', path: '/accounts', shortcut: 'g a' },
  { title: 'Debt', path: '/debt' },
  { title: 'Import', path: '/import' },
  { title: 'Insights', path: '/insights' },
  { title: 'Real Estate', path: '/real-estate', shortcut: 'g r' },
  { title: 'Retirement', path: '/retirement' },
  { title: 'Settings', path: '/settings', shortcut: 'g s' },
  { title: 'Taxes', path: '/taxes' },
] as const

const TIMEFRAME_COMMANDS = ['1M', '3M', '6M', '1Y', 'YTD', 'ALL'] as const

function commandMatches(command: Command, query: string) {
  if (!query.trim()) return true
  const haystack = `${command.title} ${command.meta} ${command.shortcut ?? ''}`.toLowerCase()
  return query.toLowerCase().trim().split(/\s+/).every((part) => haystack.includes(part))
}

export default function CommandPalette() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)

  const close = () => {
    setOpen(false)
    setQuery('')
    setActiveIndex(0)
  }

  const commands = useMemo<Command[]>(() => {
    const pages = PAGE_COMMANDS.map((page) => ({
      id: `page:${page.path}`,
      title: `Go to ${page.title}`,
      meta: 'Jump to page',
      shortcut: 'shortcut' in page ? page.shortcut : undefined,
      run: () => {
        navigate(page.path)
        close()
      },
    }))

    const timeframes = TIMEFRAME_COMMANDS.map((range) => ({
      id: `timeframe:${range}`,
      title: `Switch timeframe to ${range}`,
      meta: 'Set dashboard range',
      run: () => {
        localStorage.setItem('libertas:timeframe', range)
        window.dispatchEvent(new CustomEvent('libertas:timeframe', { detail: range }))
        close()
      },
    }))

    return [
      ...pages,
      {
        id: 'quick:add-transaction',
        title: 'Quick add transaction',
        meta: 'Open import workflow',
        run: () => {
          navigate('/import')
          close()
        },
      },
      {
        id: 'quick:add-account',
        title: 'Quick add account',
        meta: 'Open settings accounts',
        run: () => {
          navigate('/settings')
          window.dispatchEvent(new CustomEvent('libertas:settings-section', { detail: 'accounts' }))
          close()
        },
      },
      ...timeframes,
      {
        id: 'theme:toggle',
        title: 'Toggle theme',
        meta: 'Future command registered',
        run: () => {
          window.dispatchEvent(new CustomEvent('libertas:theme-toggle'))
          close()
        },
      },
    ]
  }, [navigate])

  const filtered = useMemo(() => commands.filter((command) => commandMatches(command, query)), [commands, query])

  useCommandPaletteHotkeys(() => setOpen(true))

  useChordHotkeys([
    { keys: ['g', 'a'], run: () => navigate('/accounts') },
    { keys: ['g', 'd'], run: () => navigate('/') },
    { keys: ['g', 'r'], run: () => navigate('/real-estate') },
    { keys: ['g', 's'], run: () => navigate('/settings') },
    { keys: ['?'], run: () => setOpen(true) },
  ], !open)

  useEffect(() => {
    if (!open) return
    const focusTimer = window.setTimeout(() => inputRef.current?.focus(), 0)
    return () => window.clearTimeout(focusTimer)
  }, [open])

  useEffect(() => {
    setActiveIndex(0)
  }, [query])

  useEffect(() => {
    if (!open) return undefined

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        close()
        return
      }

      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setActiveIndex((index) => Math.min(index + 1, Math.max(filtered.length - 1, 0)))
        return
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setActiveIndex((index) => Math.max(index - 1, 0))
        return
      }

      if (event.key === 'Enter') {
        event.preventDefault()
        filtered[activeIndex]?.run()
        return
      }

      if (event.key === 'Tab' && dialogRef.current) {
        const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>('input, button'))
        if (!focusable.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [activeIndex, filtered, open])

  if (!open) return null

  return (
    <div className="command-overlay" role="presentation" onMouseDown={close}>
      <div
        ref={dialogRef}
        className="command-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <input
          ref={inputRef}
          className="command-input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Type a command or page..."
          aria-label="Command"
        />
        <div className="command-results" role="listbox" aria-label="Commands">
          {filtered.length ? filtered.map((command, index) => (
            <button
              key={command.id}
              type="button"
              className={`command-row${index === activeIndex ? ' active' : ''}`}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={command.run}
              role="option"
              aria-selected={index === activeIndex}
            >
              <span>
                <span className="command-title">{command.title}</span>
                <span className="command-meta">{command.meta}</span>
              </span>
              {command.shortcut ? <kbd>{command.shortcut}</kbd> : null}
            </button>
          )) : (
            <div className="command-empty">NO COMMAND MATCH</div>
          )}
        </div>
      </div>
    </div>
  )
}
