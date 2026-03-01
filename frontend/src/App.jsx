import { Routes, Route, Link, Navigate } from 'react-router-dom'
import { LogOut, User } from 'lucide-react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { PageDataProvider } from './context/PageDataContext'
import Home from './pages/Home'
import MyDocuments from './pages/MyDocuments'
import Analysis from './pages/Analysis'
import Insights from './pages/Insights'
import Dashboard from './pages/Dashboard'
import Trends from './pages/Trends'
import ActionItems from './pages/ActionItems'
import Simulator from './pages/Simulator'
import FinancialAdvisor from './pages/FinancialAdvisor'
import AdvisorDashboard from './pages/AdvisorDashboard'
import StockResearch from './pages/StockResearch'
import StockAdvisorReview from './pages/StockAdvisorReview'
import Login from './pages/Login'
import Register from './pages/Register'
import TaxLayout from './layouts/TaxLayout'
import StocksLayout from './layouts/StocksLayout'
// import ChatWidget from './components/ChatWidget'
import { LoadingSpinner } from './components/LoadingState'
import './styles/dashboard.css'

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-8)' }}><LoadingSpinner size={24} /></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function AppContent() {
  const { isAuthenticated, user, logout } = useAuth()

  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
          <Link to="/" className="nav-brand">
            <span className="nav-logo">W</span>
            <span className="nav-brand-text">Wealthsimple</span>
          </Link>
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
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />

          {/* Tax section */}
          <Route path="/tax" element={<ProtectedRoute><TaxLayout /></ProtectedRoute>}>
            <Route path="documents" element={<MyDocuments />} />
            <Route path="analysis" element={<Analysis />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="insights" element={<Insights />} />
            <Route path="actions" element={<ActionItems />} />
            <Route path="simulator" element={<Simulator />} />
            <Route path="ai-advisor" element={<FinancialAdvisor />} />
            <Route path="trends" element={<Trends />} />
            <Route path="advisor" element={<AdvisorDashboard />} />
            <Route index element={<Navigate to="documents" replace />} />
          </Route>

          {/* Stocks section */}
          <Route path="/stocks" element={<ProtectedRoute><StocksLayout /></ProtectedRoute>}>
            <Route index element={<StockResearch />} />
            <Route path="review" element={<StockAdvisorReview />} />
          </Route>
        </Routes>
      </main>
      {/* <ChatWidget /> */}
    </>
  )
}

function App() {
  return (
    <AuthProvider>
      <PageDataProvider>
        <AppContent />
      </PageDataProvider>
    </AuthProvider>
  )
}

export default App
