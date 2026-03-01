import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Upload, AlertTriangle, Lightbulb, X, CheckCircle2, User, Home, Baby, Calendar } from 'lucide-react'
import { getUserDocuments, uploadDocument, createProfile, updateProfile } from '../services/api'
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
  const [pendingProfile, setPendingProfile] = useState(null) // { profileId, taxYear }

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
      setUploadMsg({ type: 'success', text: 'Document uploaded! Please provide your personal details.' })
      setTimeout(() => {
        setShowUpload(false)
        setUploadMsg(null)
        setPendingProfile({ profileId: profileRes.profile_id, taxYear: profileRes.tax_year })
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
        {pendingProfile && (
          <PersonalDetailsModal
            profileId={pendingProfile.profileId}
            onSkip={() => {
              setPendingProfile(null)
              navigate(`/tax/ai-advisor`)
            }}
            onSaved={() => {
              const pid = pendingProfile.profileId
              setPendingProfile(null)
              navigate(`/tax/ai-advisor`)
            }}
          />
        )}
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
    navigate(`/tax/ai-advisor`)
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
      {pendingProfile && (
        <PersonalDetailsModal
          profileId={pendingProfile.profileId}
          onSkip={() => {
            setPendingProfile(null)
            navigate(`/tax/ai-advisor`)
          }}
          onSaved={() => {
            const pid = pendingProfile.profileId
            setPendingProfile(null)
            navigate(`/tax/ai-advisor`)
          }}
        />
      )}
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

const MARITAL_OPTIONS = [
  { value: '', label: 'Select...' },
  { value: 'single', label: 'Single' },
  { value: 'married', label: 'Married' },
  { value: 'common_law', label: 'Common-law' },
  { value: 'separated', label: 'Separated' },
  { value: 'divorced', label: 'Divorced' },
  { value: 'widowed', label: 'Widowed' },
]

function PersonalDetailsModal({ profileId, onSkip, onSaved }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({
    date_of_birth: '',
    marital_status: '',
    num_children_under_18: 0,
    spouse_income: '',
    rent_paid: '',
    property_tax_paid: '',
  })

  const isFamily = form.marital_status === 'married' || form.marital_status === 'common_law'

  const set = (field, value) => setForm(prev => ({ ...prev, [field]: value }))

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const personal = {
        date_of_birth: form.date_of_birth || null,
        marital_status: form.marital_status || null,
        num_children_under_18: parseInt(form.num_children_under_18) || 0,
        spouse_income: isFamily && form.spouse_income ? parseFloat(form.spouse_income) : null,
        rent_paid: form.rent_paid ? parseFloat(form.rent_paid) : 0,
        property_tax_paid: form.property_tax_paid ? parseFloat(form.property_tax_paid) : 0,
      }
      await updateProfile(profileId, { personal_details: personal })
      onSaved()
    } catch (e) {
      setError(e.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onSkip}>
      <div className="modal-content personal-details-modal animate-fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">
            <User size={18} />
            Personal Details
          </h2>
          <button className="modal-close" onClick={onSkip}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <p className="text-muted" style={{ marginBottom: 'var(--space-4)' }}>
            These details improve the accuracy of your tax benefit calculations (OTB, CCB, GST/HST credit).
            You can skip this and provide them later.
          </p>

          <div className="personal-form-grid">
            {/* Date of Birth */}
            <div className="form-field">
              <label className="form-label">
                <Calendar size={14} /> Date of Birth
              </label>
              <input
                type="date"
                className="form-input"
                value={form.date_of_birth}
                onChange={(e) => set('date_of_birth', e.target.value)}
              />
            </div>

            {/* Marital Status */}
            <div className="form-field">
              <label className="form-label">
                <User size={14} /> Marital Status
              </label>
              <select
                className="form-input"
                value={form.marital_status}
                onChange={(e) => set('marital_status', e.target.value)}
              >
                {MARITAL_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {/* Number of Children */}
            <div className="form-field">
              <label className="form-label">
                <Baby size={14} /> Children Under 18
              </label>
              <input
                type="number"
                className="form-input"
                min="0"
                max="20"
                value={form.num_children_under_18}
                onChange={(e) => set('num_children_under_18', e.target.value)}
              />
            </div>

            {/* Spouse Income — only if married/common-law */}
            {isFamily && (
              <div className="form-field">
                <label className="form-label">
                  <User size={14} /> Spouse's Net Income ($)
                </label>
                <input
                  type="number"
                  className="form-input"
                  placeholder="0.00"
                  min="0"
                  step="100"
                  value={form.spouse_income}
                  onChange={(e) => set('spouse_income', e.target.value)}
                />
              </div>
            )}

            {/* Rent Paid */}
            <div className="form-field">
              <label className="form-label">
                <Home size={14} /> Annual Rent Paid ($)
              </label>
              <input
                type="number"
                className="form-input"
                placeholder="0.00"
                min="0"
                step="100"
                value={form.rent_paid}
                onChange={(e) => set('rent_paid', e.target.value)}
              />
              <span className="form-hint">Total rent for the tax year</span>
            </div>

            {/* Property Tax Paid */}
            <div className="form-field">
              <label className="form-label">
                <Home size={14} /> Annual Property Tax ($)
              </label>
              <input
                type="number"
                className="form-input"
                placeholder="0.00"
                min="0"
                step="100"
                value={form.property_tax_paid}
                onChange={(e) => set('property_tax_paid', e.target.value)}
              />
              <span className="form-hint">If you own your home</span>
            </div>
          </div>

          {error && (
            <div className="error-banner" style={{ marginTop: 'var(--space-4)' }}>
              <AlertTriangle size={18} className="banner-icon" />
              {error}
            </div>
          )}

          <div className="personal-form-actions">
            <button className="btn btn-ghost" onClick={onSkip}>
              Skip for Now
            </button>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <LoadingSpinner size={14} /> : <CheckCircle2 size={14} />}
              Save & Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
