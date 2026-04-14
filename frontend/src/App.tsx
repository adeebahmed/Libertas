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
