import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Import from './pages/Import'
import RealEstatePage from './pages/RealEstate'
import RetirementPage from './pages/Retirement'
import InsightsPage from './pages/Insights'
import DebtPage from './pages/Debt'
import TaxesPage from './pages/Taxes'
import Settings from './pages/Settings'

const NAV = [
  { to: '/',             label: 'Overview',    end: true },
  { to: '/accounts',    label: 'Accounts',    end: false },
  { to: '/import',      label: 'Import',      end: false },
  { to: '/real-estate', label: 'Real Estate', end: false },
  { to: '/retirement',  label: 'Retirement',  end: false },
  { to: '/debt',        label: 'Debt',        end: false },
  { to: '/taxes',       label: 'Taxes',       end: false },
  { to: '/insights',    label: 'Insights',    end: false },
  { to: '/settings',    label: 'Settings',    end: false },
]

export default function App() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar-logo">
          <span>L</span>ibertas
        </div>
        <div className="sidebar-section">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              {n.label}
            </NavLink>
          ))}
        </div>
        <div className="sidebar-footer">
          v0.1 · local
        </div>
      </nav>
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
  )
}
