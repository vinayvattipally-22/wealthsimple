import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Play, BarChart3, Lightbulb, LayoutDashboard, AlertTriangle, RotateCcw, ChevronDown, ListChecks } from 'lucide-react'
import { getAnalysisStatus, getUserDocuments } from '../services/api'
import PipelineProgress from '../components/PipelineProgress'
import EmptyState from '../components/EmptyState'
import '../styles/dashboard.css'

export default function Analysis() {
  const [searchParams] = useSearchParams()
  const urlProfileId = searchParams.get('profile_id')

  const [profiles, setProfiles] = useState([])
  const [selectedId, setSelectedId] = useState(urlProfileId ? Number(urlProfileId) : null)
  const [status, setStatus] = useState(null)
  const [step, setStep] = useState('idle')
  const [stages, setStages] = useState({})
  const [insights, setInsights] = useState([])
  const [complianceFlags, setComplianceFlags] = useState([])
  const [complete, setComplete] = useState(null)
  const [loadingProfiles, setLoadingProfiles] = useState(true)

  // Load profiles on mount
  useEffect(() => {
    getUserDocuments()
      .then((res) => {
        const docs = (res.documents || []).filter(d => d.profile_id)
        setProfiles(docs)
        // Default to URL param, or most recent profile
        if (!urlProfileId && docs.length > 0) {
          setSelectedId(docs[0].profile_id)
        }
      })
      .catch(() => {})
      .finally(() => setLoadingProfiles(false))
  }, [urlProfileId])

  // Fetch status when profile changes
  useEffect(() => {
    if (!selectedId) return
    setStatus(null)
    getAnalysisStatus(selectedId).then(setStatus).catch(() => setStatus(null))
  }, [selectedId])

  // Reset analysis state when profile changes
  const handleProfileChange = (newId) => {
    setSelectedId(newId)
    setStep('idle')
    setStages({})
    setInsights([])
    setComplianceFlags([])
    setComplete(null)
  }

  const runAnalysis = useCallback(() => {
    if (!selectedId) return
    setStep('streaming')
    setStages({})
    setInsights([])
    setComplianceFlags([])
    setComplete(null)

    const eventSource = new EventSource(`/api/analyze/${selectedId}/stream`)

    eventSource.addEventListener('stage', (e) => {
      const data = JSON.parse(e.data)
      setStages((prev) => ({
        ...prev,
        [data.stage]: data.status,
        [`${data.stage}_message`]: data.message,
        [`${data.stage}_agent_name`]: data.agent_name,
      }))
    })

    eventSource.addEventListener('insight', (e) => {
      const data = JSON.parse(e.data)
      setInsights((prev) => [...prev, data])
    })

    eventSource.addEventListener('compliance', (e) => {
      const data = JSON.parse(e.data)
      setComplianceFlags((prev) => [...prev, data])
    })

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data)
      setComplete(data)
      setStep('done')
      setStatus({ review_status: 'PENDING' })
      eventSource.close()
    })

    eventSource.onerror = () => {
      setStep('error')
      eventSource.close()
    }
  }, [selectedId])

  if (loadingProfiles) return null

  if (profiles.length === 0) {
    return (
      <div className="page-container">
        <EmptyState
          icon={BarChart3}
          title="No profiles yet"
          description="Upload a document from My Documents to run your tax analysis."
        />
      </div>
    )
  }

  const currentProfile = profiles.find(p => p.profile_id === selectedId)

  return (
    <div className="page-container" style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">Analysis</h1>
          <p className="page-subtitle">
            {status && <>Status: <strong>{status.review_status}</strong></>}
          </p>
        </div>
        {profiles.length > 0 && (
          <div className="dashboard-select-wrap">
            <select
              className="dashboard-select"
              value={selectedId || ''}
              onChange={(e) => handleProfileChange(Number(e.target.value))}
            >
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.tax_year || 'N/A'}{p.doc_type ? ` — ${p.doc_type}` : ''}
                </option>
              ))}
            </select>
            <ChevronDown size={16} className="dashboard-select-icon" />
          </div>
        )}
      </div>

      {step === 'idle' && (
        <div style={{ textAlign: 'center', padding: 'var(--space-8) 0' }}>
          <button onClick={runAnalysis} className="btn btn-primary btn-lg">
            <Play size={18} />
            Analyze My Taxes
          </button>
          <p className="text-muted" style={{ marginTop: 'var(--space-3)' }}>
            We'll find savings opportunities and personalized tax insights for you.
          </p>
        </div>
      )}

      {(step === 'streaming' || step === 'done') && (
        <PipelineProgress stages={stages} insights={insights} complianceFlags={complianceFlags} complete={complete} />
      )}

      {step === 'done' && (
        <div className="animate-fade-in-up" style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'center', marginTop: 'var(--space-6)' }}>
          <Link to={`/tax/insights?profile_id=${selectedId}`} className="btn btn-success">
            <Lightbulb size={16} />
            View Insights
          </Link>
          <Link to={`/tax/actions`} className="btn btn-primary">
            <ListChecks size={16} />
            Action Items
          </Link>
          <Link to={`/tax/dashboard`} className="btn btn-secondary">
            <LayoutDashboard size={16} />
            Dashboard
          </Link>
        </div>
      )}

      {step === 'error' && (
        <div className="animate-fade-in" style={{ textAlign: 'center', marginTop: 'var(--space-6)' }}>
          <div className="error-banner" style={{ justifyContent: 'center', marginBottom: 'var(--space-4)' }}>
            <AlertTriangle size={18} className="banner-icon" />
            Analysis failed. Check the backend connection and try again.
          </div>
          <button onClick={() => setStep('idle')} className="btn btn-secondary">
            <RotateCcw size={16} />
            Retry
          </button>
        </div>
      )}
    </div>
  )
}
