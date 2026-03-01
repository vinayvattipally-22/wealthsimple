import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Download, Lightbulb, AlertTriangle, ChevronDown } from 'lucide-react'
import InsightCard from '../components/InsightCard'
import SavingsSummary from '../components/SavingsSummary'
import ReviewPendingBanner from '../components/ReviewPendingBanner'
import { LoadingSpinner, PageLoading } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { getAnalysisResults, downloadReport, getUserDocuments } from '../services/api'
import { usePageData } from '../context/PageDataContext'
import '../styles/dashboard.css'

export default function Insights() {
  const [searchParams] = useSearchParams()
  const urlProfileId = searchParams.get('profile_id')

  const [profiles, setProfiles] = useState([])
  const [selectedId, setSelectedId] = useState(urlProfileId ? Number(urlProfileId) : null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [downloading, setDownloading] = useState(false)
  const { setPageData } = usePageData()

  // Load profiles on mount
  useEffect(() => {
    getUserDocuments()
      .then((res) => {
        const docs = (res.documents || []).filter(d => d.profile_id)
        setProfiles(docs)
        // Default to URL param, or most recent profile with insights, or just first
        if (!urlProfileId && docs.length > 0) {
          const withInsights = docs.find(d => d.insights_count > 0)
          setSelectedId(withInsights ? withInsights.profile_id : docs[0].profile_id)
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!urlProfileId) setLoading(false)
      })
  }, [urlProfileId])

  // Fetch insights when profile changes
  useEffect(() => {
    if (!selectedId) return
    setLoading(true)
    setError(null)
    setData(null)
    getAnalysisResults(selectedId)
      .then((res) => {
        setData(res)
        setPageData({ page: 'insights', data: res })
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedId, setPageData])

  const handleDownloadPDF = async () => {
    if (!selectedId) return
    setDownloading(true)
    try {
      const blob = await downloadReport(selectedId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `tax_insights_${selectedId}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      alert('Failed to download report: ' + e.message)
    } finally {
      setDownloading(false)
    }
  }

  if (loading) return <PageLoading />

  if (profiles.length === 0 && !selectedId) {
    return (
      <div className="page-container">
        <EmptyState
          icon={Lightbulb}
          title="No reports yet"
          description="Upload a document from My Documents and run an analysis to see your insights."
        />
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-header-text">
            <h1 className="page-title">Insights</h1>
          </div>
          {profiles.length > 0 && (
            <div className="dashboard-select-wrap">
              <select
                className="dashboard-select"
                value={selectedId || ''}
                onChange={(e) => setSelectedId(Number(e.target.value))}
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
        <div className="error-banner">
          <AlertTriangle size={20} className="banner-icon" />
          {error}
        </div>
      </div>
    )
  }

  const insights = data?.insights ?? []
  const summary = data?.summary ?? {}
  const reviewPending = data?.review_pending === true
  const totalSavings = insights.reduce((s, i) => s + (i.estimated_value || 0), 0)
  const currentProfile = profiles.find(p => p.profile_id === selectedId)

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">Insights</h1>
          <p className="page-subtitle">
            {insights.length > 0
              ? `${insights.length} insights found${currentProfile ? ` · ${currentProfile.tax_year || ''}` : ''}`
              : currentProfile ? `${currentProfile.tax_year || ''}` : ''
            }
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
          {profiles.length > 0 && (
            <div className="dashboard-select-wrap">
              <select
                className="dashboard-select"
                value={selectedId || ''}
                onChange={(e) => setSelectedId(Number(e.target.value))}
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
          {insights.length > 0 && (
            <button
              onClick={handleDownloadPDF}
              disabled={downloading}
              className="btn btn-primary"
            >
              {downloading ? (
                <><LoadingSpinner size={14} /> Generating...</>
              ) : (
                <><Download size={16} /> Download PDF</>
              )}
            </button>
          )}
        </div>
      </div>

      <SavingsSummary summary={{ total_identified_savings: totalSavings, act_now_count: summary.act_now_count, this_year_count: summary.this_year_count, long_term_count: summary.long_term_count }} />

      {insights.length === 0 && reviewPending ? (
        <ReviewPendingBanner message="Your tax insights are being reviewed by a financial advisor. Once approved, they will appear here with estimated savings." />
      ) : insights.length === 0 ? (
        <EmptyState
          icon={Lightbulb}
          title="No insights yet"
          description="Run an analysis to generate personalized tax insights."
        />
      ) : (
        <div>
          {reviewPending && <ReviewPendingBanner message="Some insights may still be under advisor review. Only approved insights are shown below." />}
          {insights.map((ins, i) => <InsightCard key={i} insight={ins} />)}
        </div>
      )}
    </div>
  )
}
