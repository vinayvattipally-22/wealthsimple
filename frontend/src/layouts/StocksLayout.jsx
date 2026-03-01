import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, CandlestickChart, Shield } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const STOCKS_NAV_ITEMS = [
  { to: '/stocks', label: 'Research', icon: CandlestickChart },
]

const ADVISOR_NAV_ITEMS = [
  { to: '/stocks/review', label: 'Review Queue', icon: Shield },
]

export default function StocksLayout() {
  const location = useLocation()
  const { isAdvisor } = useAuth()
  const items = isAdvisor ? ADVISOR_NAV_ITEMS : STOCKS_NAV_ITEMS

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
