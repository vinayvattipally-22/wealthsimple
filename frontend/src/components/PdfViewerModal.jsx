import { useEffect, useState } from 'react'
import { X, FileText } from 'lucide-react'
import { getAuthToken } from '../services/api'
import { LoadingSpinner } from './LoadingState'

export default function PdfViewerModal({ documentId, fileName, onClose }) {
  const [blobUrl, setBlobUrl] = useState(null)
  const [error, setError] = useState(null)

  // Fetch PDF bytes with auth header, create blob URL
  useEffect(() => {
    let revoked = false
    const token = getAuthToken()
    fetch(`/api/documents/${documentId}/view`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load document (${res.status})`)
        return res.blob()
      })
      .then((blob) => {
        if (revoked) return
        const url = URL.createObjectURL(blob)
        setBlobUrl(url)
      })
      .catch((e) => {
        if (!revoked) setError(e.message)
      })
    return () => {
      revoked = true
      if (blobUrl) URL.revokeObjectURL(blobUrl)
    }
  }, [documentId])

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  // Prevent body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  // Clean up blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl)
    }
  }, [blobUrl])

  return (
    <div className="pdf-viewer-overlay" onClick={onClose}>
      <div className="pdf-viewer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="pdf-viewer-header">
          <div className="pdf-viewer-title">
            <FileText size={16} />
            <span>{fileName || 'Document'}</span>
            <span className="pdf-viewer-badge">Redacted</span>
          </div>
          <button className="pdf-viewer-close" onClick={onClose} title="Close (Esc)">
            <X size={20} />
          </button>
        </div>
        <div className="pdf-viewer-body">
          {error ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--ws-red)' }}>
              {error}
            </div>
          ) : !blobUrl ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 8 }}>
              <LoadingSpinner size={20} />
              <span>Loading document...</span>
            </div>
          ) : (
            <iframe
              src={blobUrl}
              className="pdf-viewer-iframe"
              title="Document Viewer"
            />
          )}
        </div>
      </div>
    </div>
  )
}
