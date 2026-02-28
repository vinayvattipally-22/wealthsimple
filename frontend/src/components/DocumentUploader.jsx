import { useState, useCallback } from 'react'
import { Upload, FileText, AlertTriangle } from 'lucide-react'

const MAX_MB = 10
const MAX_BYTES = MAX_MB * 1024 * 1024
const ACCEPT = '.pdf'

export default function DocumentUploader({ onUpload, disabled }) {
  const [drag, setDrag] = useState(false)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)

  const validate = useCallback((file) => {
    setError(null)
    if (!file) return false
    if (file.size > MAX_BYTES) {
      setError(`File must be under ${MAX_MB}MB`)
      return false
    }
    const ext = (file.name || '').toLowerCase()
    if (!ext.endsWith('.pdf')) {
      setError('Only PDF files are supported')
      return false
    }
    return true
  }, [])

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault()
      setDrag(false)
      const file = e.dataTransfer?.files?.[0]
      if (!validate(file)) return
      setPreview(file.name)
      onUpload?.(file)
    },
    [onUpload, validate]
  )

  const handleChange = useCallback(
    (e) => {
      const file = e.target?.files?.[0]
      if (!validate(file)) return
      setPreview(file.name)
      onUpload?.(file)
    },
    [onUpload, validate]
  )

  const zoneClass = [
    'upload-zone',
    drag ? 'upload-zone-active' : '',
    disabled ? 'upload-zone-disabled' : '',
  ].filter(Boolean).join(' ')

  return (
    <div>
      <div
        className={zoneClass}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept={ACCEPT}
          onChange={handleChange}
          style={{ display: 'none' }}
          id="doc-upload"
        />
        <label htmlFor="doc-upload" style={{ cursor: disabled ? 'not-allowed' : 'pointer', display: 'block' }}>
          <Upload size={40} className="upload-icon" strokeWidth={1.5} />
          <p className="upload-title">Drop your tax document here</p>
          <p className="upload-hint">or click to browse &middot; PDF only, max {MAX_MB}MB</p>
          <div className="upload-formats">
            <span className="upload-format-tag">PDF</span>
          </div>
        </label>
      </div>

      {preview && (
        <div className="file-preview">
          <FileText size={20} className="file-preview-icon" />
          <span className="file-preview-name">{preview}</span>
        </div>
      )}

      {error && (
        <div className="error-banner" style={{ marginTop: 'var(--space-3)' }}>
          <AlertTriangle size={16} className="banner-icon" />
          {error}
        </div>
      )}
    </div>
  )
}
