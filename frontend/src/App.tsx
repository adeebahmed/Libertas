import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Import from './pages/Import'
import RealEstatePage from './pages/RealEstate'
import Projections from './pages/Projections'
import InsightsPage from './pages/Insights'
import Settings from './pages/Settings'

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/accounts', label: 'Accounts' },
  { to: '/import', label: 'Import' },
  { to: '/real-estate', label: 'Real Estate' },
  { to: '/projections', label: 'Projections' },
  { to: '/insights', label: 'Insights' },
  { to: '/settings', label: 'Settings' },
]

export default function App() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar-logo">Libertas</div>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/'}
            className={({ isActive }) => (isActive ? 'active' : '')}
          >
            {n.label}
          </NavLink>
        ))}
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/import" element={<Import />} />
          <Route path="/real-estate" element={<RealEstatePage />} />
          <Route path="/projections" element={<Projections />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
