import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, AlertTriangle } from 'lucide-react'
import DocumentUploader from '../components/DocumentUploader'
import { LoadingSpinner } from '../components/LoadingState'
import { uploadDocument, createProfile } from '../services/api'

export default function Upload() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)

  const handleUpload = async (file) => {
    if (!file) return
    setLoading(true)
    setMessage(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const extracted = await uploadDocument(formData)
      if (extracted.error) {
        setMessage({ type: 'error', text: extracted.error })
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
      setMessage({ type: 'success', text: `Profile #${profileRes.profile_id} created. Redirecting to analysis...` })
      navigate(`/tax/analysis?profile_id=${profileRes.profile_id}`)
    } catch (e) {
      setMessage({ type: 'error', text: e.message || 'Upload failed' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container" style={{ maxWidth: 640 }}>
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">Upload Tax Documents</h1>
          <p className="page-subtitle">
            Upload your T4, T5, or RRSP document. We'll extract the data and prepare your analysis.
          </p>
        </div>
      </div>

      <DocumentUploader onUpload={handleUpload} disabled={loading} />

      {loading && (
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
  )
}
