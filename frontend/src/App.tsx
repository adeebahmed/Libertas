import { useState, useEffect } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import CommandPalette from './components/CommandPalette'
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
  IconHouse, IconReceipt, IconSpark, IconUpload, IconGear,
} from './components/Icons'

const NAV = [
  { to: '/',             label: 'Overview',    end: true,  icon: <IconGrid /> },
  { to: '/accounts',    label: 'Accounts',    end: false, icon: <IconWallet /> },
  { to: '/debt',        label: 'Debt',        end: false, icon: <IconTrendDown /> },
  { to: '/retirement',  label: 'Retirement',  end: false, icon: <IconBarChart /> },
  { to: '/real-estate', label: 'Real Estate', end: false, icon: <IconHouse /> },
  { to: '/taxes',       label: 'Taxes',       end: false, icon: <IconReceipt /> },
  { to: '/insights',    label: 'Insights',    end: false, icon: <IconSpark /> },
]

const ROUTE_TITLES: Array<{ path: string; title: string; exact?: boolean }> = [
  { path: '/', title: 'Overview', exact: true },
  { path: '/accounts', title: 'Accounts' },
  { path: '/debt', title: 'Debt' },
  { path: '/retirement', title: 'Retirement' },
  { path: '/real-estate', title: 'Real Estate' },
  { path: '/taxes', title: 'Taxes' },
  { path: '/insights', title: 'Insights' },
  { path: '/import', title: 'Import' },
  { path: '/settings', title: 'Settings' },
]

export default function App() {
  const location = useLocation()

  const [theme, setTheme] = useState<'onyx' | 'chalk'>(() =>
    (localStorage.getItem('libertas-theme') as 'onyx' | 'chalk') ?? 'onyx'
  )

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('libertas-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'onyx' ? 'chalk' : 'onyx')
  const activeTitle = ROUTE_TITLES.find((route) => (
    route.exact ? location.pathname === route.path : location.pathname.startsWith(route.path)
  ))?.title ?? 'Libertas'

  return (
    <div className="app">
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
          <button className="btn btn-sm" onClick={toggleTheme} title="Switch theme">
            {theme === 'onyx' ? 'Chalk' : 'Onyx'}
          </button>
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
          <a
            className="sidebar-logo-link"
            href="https://adeebahmed.github.io/Libertas/"
            target="_blank"
            rel="noreferrer"
            title="Open Libertas GitHub Pages site"
          >
            Libertas
          </a>
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
              {n.label}
            </NavLink>
          ))}
        </div>
        <div className="sidebar-footer">
          <div className="sidebar-hotkey">
            <span>Press</span>
            <kbd>⌘K</kbd>
          </div>
          <NavLink to="/import" className="sidebar-import-btn">
            <IconUpload size={13} />
            Import
          </NavLink>
          <NavLink to="/settings" className="sidebar-icon-btn" title="Settings">
            <IconGear size={14} />
          </NavLink>
        </div>
      </nav>
      <CommandPalette />
      <main className="main">
        <header className="app-header">
          <div className="app-header-title">
            <span className="app-header-brand">Libertas</span>
            <span className="app-header-rule" aria-hidden="true" />
            <span>{activeTitle}</span>
          </div>
          <div className="app-header-actions">
            <button className="btn btn-sm" onClick={toggleTheme} title="Switch theme">
              {theme === 'onyx' ? 'Chalk' : 'Onyx'}
            </button>
          </div>
        </header>
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
  )
}
