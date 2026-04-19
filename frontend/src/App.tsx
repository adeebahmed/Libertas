import { useEffect, useState } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import CommandPalette from './components/CommandPalette'
import { ThemeProvider } from './theme'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Import from './pages/Import'
import RealEstatePage from './pages/RealEstate'
import RetirementPage from './pages/Retirement'
import InsightsPage from './pages/Insights'
import DebtPage from './pages/Debt'
import TaxesPage from './pages/Taxes'
import Settings from './pages/Settings'
import {
  IconGrid, IconWallet, IconTrendDown, IconBarChart,
  IconHouse, IconReceipt, IconSearch, IconUpload, IconGear, IconChevronLeft,
} from './components/Icons'

const NAV = [
  { to: '/',             label: 'Overview',    end: true,  icon: <IconGrid />,      hotkey: 'o' },
  { to: '/accounts',    label: 'Accounts',    end: false, icon: <IconWallet />,    hotkey: 'a' },
  { to: '/debt',        label: 'Debt',        end: false, icon: <IconTrendDown />, hotkey: 'd' },
  { to: '/retirement',  label: 'Retirement',  end: false, icon: <IconBarChart />,  hotkey: 'r' },
  { to: '/real-estate', label: 'Real Estate', end: false, icon: <IconHouse />,     hotkey: 'e', hotkeyIndex: 5 },
  { to: '/taxes',       label: 'Taxes',       end: false, icon: <IconReceipt />,   hotkey: 't' },
  { to: '/insights',    label: 'Insights',    end: false, icon: <IconSearch />,    hotkey: 'i' },
]

const FOOTER_NAV = [
  { to: '/import',   label: 'Import',   hotkey: 'm', icon: <IconUpload size={13} /> },
  { to: '/settings', label: 'Settings', hotkey: 's', icon: <IconGear size={13} /> },
]

function NavLabel({ label, hotkey, hotkeyIndex }: { label: string; hotkey?: string; hotkeyIndex?: number }) {
  if (!hotkey) return <span>{label}</span>
  const idx = hotkeyIndex !== undefined ? hotkeyIndex : label.toLowerCase().indexOf(hotkey)
  if (idx === -1) return <span>{label}</span>
  return (
    <span>
      {label.slice(0, idx)}
      <u style={{ textDecorationThickness: '1px', textUnderlineOffset: '2px' }}>{label[idx]}</u>
      {label.slice(idx + 1)}
    </span>
  )
}

export default function App() {
  const navigate = useNavigate()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem('libertas:sidebar-collapsed') === '1'
  })

  useEffect(() => {
    window.localStorage.setItem('libertas:sidebar-collapsed', sidebarCollapsed ? '1' : '0')
  }, [sidebarCollapsed])

  useEffect(() => {
    const isEditableTarget = (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement)) return false
      const tag = target.tagName.toLowerCase()
      return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable
    }

    const allNav = [...NAV, ...FOOTER_NAV]
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || isEditableTarget(event.target)) return
      const key = event.key
      if (key === 'ArrowLeft' || key === 'Left') {
        event.preventDefault()
        setSidebarCollapsed(true)
      } else if (key === 'ArrowRight' || key === 'Right') {
        event.preventDefault()
        setSidebarCollapsed(false)
      } else {
        const match = allNav.find(n => n.hotkey === key.toLowerCase())
        if (match) {
          event.preventDefault()
          navigate(match.to)
        }
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <ThemeProvider>
    <div className={`app${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      <header className="mobile-topbar">
        <div className="mobile-topbar-brand">
          <a
            className="mobile-topbar-brand-link"
            href="https://adeebahmed.github.io/Libertas/"
            target="_blank"
            rel="noreferrer"
            title="Open Libertas GitHub Pages site"
          >
            <span className="logo-mark">L</span>
            <span>Libertas</span>
          </a>
        </div>
        <div className="mobile-topbar-actions">
          <NavLink to="/import" className="sidebar-import-btn">
            <IconUpload size={13} />
            Import
          </NavLink>
          <NavLink to="/settings" className="sidebar-icon-btn" title="Settings">
            <IconGear size={14} />
          </NavLink>
        </div>
      </header>

      <nav className="mobile-nav">
        {NAV.map((n) => (
          <NavLink
            key={`mobile-${n.to}`}
            to={n.to}
            end={n.end}
            className={({ isActive }) => (isActive ? 'active' : '')}
          >
            {n.icon}
            {n.label}
          </NavLink>
        ))}
      </nav>

      <nav className="sidebar">
        <div className="sidebar-logo">
          {sidebarCollapsed ? (
            <button
              type="button"
              className="sidebar-logo-link sidebar-logo-expand-btn"
              onClick={() => setSidebarCollapsed(false)}
              aria-label="Expand sidebar"
              title="Expand sidebar"
            >
              <span className="logo-mark">L</span>
            </button>
          ) : (
            <>
              <a
                className="sidebar-logo-link"
                href="https://adeebahmed.github.io/Libertas/"
                target="_blank"
                rel="noreferrer"
                title="Open Libertas GitHub Pages site"
              >
                <span><span className="logo-mark">L</span>ibertas</span>
              </a>
              <button
                type="button"
                className="sidebar-collapse-btn"
                onClick={() => setSidebarCollapsed(true)}
                aria-label="Collapse sidebar"
                title="Collapse sidebar"
              >
                <IconChevronLeft size={14} />
              </button>
            </>
          )}
        </div>
        <div className="sidebar-section">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              {n.icon}
              <NavLabel label={n.label} hotkey={n.hotkey} hotkeyIndex={'hotkeyIndex' in n ? n.hotkeyIndex : undefined} />
            </NavLink>
          ))}
        </div>
        <div className="sidebar-footer">
          <div className="sidebar-cmd-hint">
            <span>{sidebarCollapsed ? '/' : 'Commands'}</span>
            <kbd>Press /</kbd>
          </div>
          <div className="sidebar-footer-row">
            {FOOTER_NAV.map((n) => (
              <NavLink key={n.to} to={n.to} className={({ isActive }) => `sidebar-footer-btn${isActive ? ' active' : ''}`}>
                {n.icon}
                <NavLabel label={n.label} hotkey={n.hotkey} />
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
      <CommandPalette />
      <main className="main">
        <Routes>
          <Route path="/"             element={<Dashboard />} />
          <Route path="/accounts"     element={<Accounts />} />
          <Route path="/import"       element={<Import />} />
          <Route path="/real-estate"  element={<RealEstatePage />} />
          <Route path="/retirement"   element={<RetirementPage />} />
          <Route path="/debt"         element={<DebtPage />} />
          <Route path="/taxes"        element={<TaxesPage />} />
          <Route path="/insights"     element={<InsightsPage />} />
          <Route path="/settings"     element={<Settings />} />
        </Routes>
      </main>
    </div>
    </ThemeProvider>
  )
}
