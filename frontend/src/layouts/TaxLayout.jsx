import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, FileText, BrainCircuit, LayoutDashboard, ListChecks, FlaskConical, TrendingUp, Shield } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const TAX_NAV_ITEMS = [
  { to: '/tax/documents', label: 'My Docs', icon: FileText },
  { to: '/tax/ai-advisor', label: 'Advisor', icon: BrainCircuit },
  { to: '/tax/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/tax/actions', label: 'Actions', icon: ListChecks },
  { to: '/tax/simulator', label: 'Simulator', icon: FlaskConical },
  { to: '/tax/trends', label: 'Trends', icon: TrendingUp },
]

const ADVISOR_NAV_ITEMS = [
  { to: '/tax/advisor', label: 'Review Queue', icon: Shield },
]

export default function TaxLayout() {
  const location = useLocation()
  const { isAdvisor } = useAuth()

  const items = isAdvisor ? ADVISOR_NAV_ITEMS : TAX_NAV_ITEMS

  return (
    <>
      <div className="section-nav">
        <div className="section-nav-inner">
          <Link to="/" className="section-nav-back" title="Back to Home">
            <Home size={16} />
            <span>Home</span>
          </Link>
          <div className="section-nav-divider" />
          <div className="section-nav-links">
            {items.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={`nav-link ${location.pathname === to ? 'nav-link-active' : ''}`}
              >
                <Icon size={16} />
                <span>{label}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
      <Outlet />
    </>
  )
}
