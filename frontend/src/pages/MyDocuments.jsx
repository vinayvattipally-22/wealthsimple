import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Upload, AlertTriangle, Lightbulb, X, CheckCircle2 } from 'lucide-react'
import { getUserDocuments, uploadDocument, createProfile } from '../services/api'
import { PageLoading, LoadingSpinner } from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import DocumentUploader from '../components/DocumentUploader'
import '../styles/dashboard.css'

export default function MyDocuments() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)

  const fetchDocs = () => {
    setLoading(true)
    getUserDocuments()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchDocs() }, [])

  const handleUpload = async (file) => {
    if (!file) return
    setUploading(true)
    setUploadMsg(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const extracted = await uploadDocument(formData)
      if (extracted.error) {
        setUploadMsg({ type: 'error', text: extracted.error })
        return
      }
      const employment = {
        total_employment_income: extracted['14'] ?? extracted.box_values?.['14'] ?? 0,
        total_cpp_contributions: extracted['16'] ?? extracted.box_values?.['16'] ?? 0,
        total_ei_premiums: extracted['18'] ?? extracted.box_values?.['18'] ?? 0,
        total_income_tax_withheld: extracted['22'] ?? extracted.box_values?.['22'] ?? 0,
        province_of_employment: extracted.province_code ?? 'ON',
      }
      const profileRes = await createProfile({
        tax_year: extracted.tax_year ?? new Date().getFullYear(),
        province_code: extracted.province_code ?? 'ON',
        employment,
        box_values: extracted,
        document_id: extracted.document_id,
      })
      setUploadMsg({ type: 'success', text: 'Document uploaded. Redirecting to analysis...' })
      setTimeout(() => {
        setShowUpload(false)
        navigate(`/analysis?profile_id=${profileRes.profile_id}`)
      }, 800)
    } catch (e) {
      setUploadMsg({ type: 'error', text: e.message || 'Upload failed' })
    } finally {
      setUploading(false)
    }
  }

  if (loading) return <PageLoading />

  if (error) {
    return (
      <div className="page-container">
        <div className="error-banner">
          <AlertTriangle size={20} className="banner-icon" />
          {error}
        </div>
      </div>
    )
  }

  const documents = data?.documents ?? []

  if (documents.length === 0) {
    return (
      <div className="page-container">
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Upload your first tax document to get started with AI-powered tax analysis."
          action={<button onClick={() => setShowUpload(true)} className="btn btn-primary"><Upload size={16} /> Upload Document</button>}
        />
        {showUpload && <UploadModal onClose={() => { setShowUpload(false); setUploadMsg(null) }} onUpload={handleUpload} uploading={uploading} message={uploadMsg} />}
      </div>
    )
  }

  const totalSavings = documents.reduce((s, d) => s + (d.total_savings || 0), 0)
  const totalInsights = documents.reduce((s, d) => s + (d.insights_count || 0), 0)

  const statusBadge = (status) => {
    if (!status) return <span className="badge badge-neutral">No Analysis</span>
    const map = { PENDING: 'badge-medium', APPROVED: 'badge-low', REJECTED: 'badge-high' }
    return <span className={`badge ${map[status] || 'badge-neutral'}`}>{status}</span>
  }

  const handleRowClick = (doc) => {
    if (!doc.profile_id) return
    if (doc.insights_count > 0) {
      navigate(`/insights?profile_id=${doc.profile_id}`)
    } else {
      navigate(`/analysis?profile_id=${doc.profile_id}`)
    }
  }

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">My Documents</h1>
          <p className="page-subtitle">{documents.length} document{documents.length !== 1 ? 's' : ''} uploaded</p>
        </div>
        <button onClick={() => setShowUpload(true)} className="btn btn-primary">
          <Upload size={16} /> Upload New
        </button>
      </div>

      <div className="summary-cards">
        <div className="summary-card">
          <div className="summary-card-icon blue"><FileText size={20} /></div>
          <div className="label">Documents</div>
          <div className="value">{documents.length}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-icon green"><Lightbulb size={20} /></div>
          <div className="label">Total Insights</div>
          <div className="value">{totalInsights}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-icon amber">
            <span style={{ fontWeight: 700, fontSize: 'var(--text-lg)' }}>$</span>
          </div>
          <div className="label">Total Savings Found</div>
          <div className="value green">${totalSavings.toLocaleString('en-CA', { minimumFractionDigits: 2 })}</div>
        </div>
      </div>

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Type</th>
              <th>Tax Year</th>
              <th>Province</th>
              <th>Status</th>
              <th>Insights</th>
              <th className="text-right">Savings</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc, i) => (
              <tr
                key={doc.document_id || doc.profile_id || i}
                onClick={() => handleRowClick(doc)}
                style={{ cursor: doc.profile_id ? 'pointer' : 'default' }}
              >
                <td style={{ fontWeight: 'var(--font-medium)' }}>
                  {doc.file_name || `Profile #${doc.profile_id}`}
                </td>
                <td>{doc.doc_type ? <span className="badge badge-info">{doc.doc_type}</span> : '—'}</td>
                <td>{doc.tax_year || '—'}</td>
                <td>{doc.province || '—'}</td>
                <td>{statusBadge(doc.review_status)}</td>
                <td>{doc.insights_count}</td>
                <td className="text-right" style={{ color: 'var(--ws-green)', fontWeight: 'var(--font-semibold)' }}>
                  ${(doc.total_savings || 0).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showUpload && <UploadModal onClose={() => { setShowUpload(false); setUploadMsg(null) }} onUpload={handleUpload} uploading={uploading} message={uploadMsg} />}
    </div>
  )
}

function UploadModal({ onClose, onUpload, uploading, message }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content animate-fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Upload Tax Document</h2>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <DocumentUploader onUpload={onUpload} disabled={uploading} />

          {uploading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 'var(--space-4)' }}>
              <LoadingSpinner size={18} />
              <span className="text-muted">Uploading and extracting data...</span>
            </div>
          )}

          {message && message.type === 'success' && (
            <div className="success-banner" style={{ marginTop: 'var(--space-4)' }}>
              <CheckCircle2 size={18} className="banner-icon" />
              {message.text}
            </div>
          )}

          {message && message.type === 'error' && (
            <div className="error-banner" style={{ marginTop: 'var(--space-4)' }}>
              <AlertTriangle size={18} className="banner-icon" />
              {message.text}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
