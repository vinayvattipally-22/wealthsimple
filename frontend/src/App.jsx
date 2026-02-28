import { useState } from 'react'
import { Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { BarChart3, LayoutDashboard, Lightbulb, TrendingUp, Shield, Menu, X, LogOut, User, FileText, ListChecks, FlaskConical, BrainCircuit } from 'lucide-react'
import { AuthProvider, useAuth } from './context/AuthContext'
import MyDocuments from './pages/MyDocuments'
import Analysis from './pages/Analysis'
import Insights from './pages/Insights'
import Dashboard from './pages/Dashboard'
import Trends from './pages/Trends'
import ActionItems from './pages/ActionItems'
import Simulator from './pages/Simulator'
import FinancialAdvisor from './pages/FinancialAdvisor'
import AdvisorDashboard from './pages/AdvisorDashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import ChatWidget from './components/ChatWidget'
import { LoadingSpinner } from './components/LoadingState'
import './styles/dashboard.css'

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-8)' }}><LoadingSpinner size={24} /></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function NavLink({ to, label, icon: Icon, onClick }) {
  const location = useLocation()
  const active = location.pathname === to
  return (
    <Link
      to={to}
      className={`nav-link ${active ? 'nav-link-active' : ''}`}
      onClick={onClick}
    >
      <Icon size={16} />
      <span>{label}</span>
    </Link>
  )
}

function AppContent() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { isAuthenticated, isAdvisor, user, logout } = useAuth()

  const NAV_ITEMS = [
    { to: '/', label: 'My Docs', icon: FileText },
    { to: '/analysis', label: 'Analysis', icon: BarChart3 },
    { to: '/ai-advisor', label: 'AI Advisor', icon: BrainCircuit },
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/insights', label: 'Insights', icon: Lightbulb },
    { to: '/actions', label: 'Actions', icon: ListChecks },
    { to: '/simulator', label: 'Simulator', icon: FlaskConical },
    { to: '/trends', label: 'Trends', icon: TrendingUp },
    ...(isAdvisor ? [{ to: '/advisor', label: 'Advisor', icon: Shield }] : []),
  ]

  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
          <Link to="/" className="nav-brand">
            <span className="nav-logo">W</span>
            <span className="nav-brand-text">Tax Analyzer</span>
          </Link>
          {isAuthenticated && (
            <div className={`nav-links ${mobileOpen ? 'nav-links-open' : ''}`}>
              {NAV_ITEMS.map(item => (
                <NavLink
                  key={item.to}
                  {...item}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </div>
          )}
          {isAuthenticated && (
            <div className="nav-user">
              <span className="nav-user-name">
                <User size={14} />
                {user?.name || user?.email}
              </span>
              <button className="btn btn-ghost btn-sm" onClick={logout} title="Sign out">
                <LogOut size={16} />
              </button>
            </div>
          )}
          {isAuthenticated && (
            <button
              className="nav-mobile-toggle"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          )}
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<ProtectedRoute><MyDocuments /></ProtectedRoute>} />
          <Route path="/analysis" element={<ProtectedRoute><Analysis /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/insights" element={<ProtectedRoute><Insights /></ProtectedRoute>} />
          <Route path="/actions" element={<ProtectedRoute><ActionItems /></ProtectedRoute>} />
          <Route path="/simulator" element={<ProtectedRoute><Simulator /></ProtectedRoute>} />
          <Route path="/ai-advisor" element={<ProtectedRoute><FinancialAdvisor /></ProtectedRoute>} />
          <Route path="/trends" element={<ProtectedRoute><Trends /></ProtectedRoute>} />
          <Route path="/advisor" element={<ProtectedRoute><AdvisorDashboard /></ProtectedRoute>} />
        </Routes>
      </main>
      <ChatWidget />
    </>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
