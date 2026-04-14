import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Import from './pages/Import'
import RealEstatePage from './pages/RealEstate'
import RetirementPage from './pages/Retirement'
import InsightsPage from './pages/Insights'
import DebtPage from './pages/Debt'
import TaxesPage from './pages/Taxes'
import Settings from './pages/Settings'
import Onboarding from './pages/Onboarding'
import { useApi } from './hooks/useApi'
import { api } from './api/client'
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

export default function App() {
  const location = useLocation()
  const { data: onboarding, loading, refetch } = useApi<{
    should_run_onboarding: boolean
  }>(() => api.get('/settings/onboarding/status'), [])

  if (loading) {
    return (
      <div className="app">
        <main className="main">
          <div className="card">Loading…</div>
        </main>
      </div>
    )
  }

  const onboardingForced = onboarding?.should_run_onboarding ?? false
  const isOnboardingRoute = location.pathname === '/onboarding'

  if (onboardingForced && !isOnboardingRoute) {
    return <Navigate to="/onboarding" replace />
  }

  return (
    <div className="app">
      {!isOnboardingRoute && (
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
      )}

      {!isOnboardingRoute && (
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
      )}

      {!isOnboardingRoute && (
      <nav className="sidebar">
        <div className="sidebar-logo">
          <a
            className="sidebar-logo-link"
            href="https://adeebahmed.github.io/Libertas/"
            target="_blank"
            rel="noreferrer"
            title="Open Libertas GitHub Pages site"
          >
            <span className="logo-mark">L</span>ibertas
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
          <NavLink to="/import" className="sidebar-import-btn">
            <IconUpload size={13} />
            Import
          </NavLink>
          <NavLink to="/settings" className="sidebar-icon-btn" title="Settings">
            <IconGear size={14} />
          </NavLink>
        </div>
      </nav>
      )}
      <main className="main">
        <Routes>
          <Route path="/onboarding"    element={<Onboarding onComplete={refetch} />} />
          <Route path="/"             element={<Dashboard />} />
          <Route path="/accounts"     element={<Accounts />} />
          <Route path="/import"       element={<Import />} />
          <Route path="/real-estate"  element={<RealEstatePage />} />
          <Route path="/retirement"   element={<RetirementPage />} />
          <Route path="/debt"         element={<DebtPage />} />
          <Route path="/taxes"        element={<TaxesPage />} />
          <Route path="/insights"     element={<InsightsPage />} />
          <Route path="/settings"     element={<Settings />} />
          <Route path="*"             element={<Navigate to={onboardingForced ? "/onboarding" : "/"} replace />} />
        </Routes>
      </main>
    </div>
  )
}
