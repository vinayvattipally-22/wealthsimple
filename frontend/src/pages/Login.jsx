import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogIn, AlertTriangle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { LoadingSpinner } from '../components/LoadingState'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container" style={{ maxWidth: 440, marginTop: 'var(--space-8)' }}>
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-6)' }}>
        <div className="nav-logo" style={{ width: 56, height: 56, fontSize: 24, margin: '0 auto var(--space-4)' }}>W</div>
        <h1 className="page-title">Welcome back</h1>
        <p className="page-subtitle">Sign in to your Tax Analyzer account</p>
      </div>

      <div className="card">
        <div className="card-body">
          {error && (
            <div className="error-banner" style={{ marginBottom: 'var(--space-4)' }}>
              <AlertTriangle size={16} className="banner-icon" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input
                type="email"
                className="form-input"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-input"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                minLength={6}
              />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: 'var(--space-3)' }} disabled={loading}>
              {loading ? <LoadingSpinner size={16} /> : <><LogIn size={16} /> Sign In</>}
            </button>
          </form>

          <p style={{ textAlign: 'center', marginTop: 'var(--space-4)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
            Don't have an account?{' '}
            <Link to="/register" style={{ color: 'var(--primary)', fontWeight: 500 }}>Create one</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
