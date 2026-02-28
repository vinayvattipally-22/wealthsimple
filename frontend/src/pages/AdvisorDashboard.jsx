import { useState } from 'react'
import ReviewQueue from '../components/ReviewQueue'
import CaseDetail from '../components/CaseDetail'
import '../styles/dashboard.css'

export default function AdvisorDashboard() {
  const [selectedCaseId, setSelectedCaseId] = useState(null)

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-header-text">
          <h1 className="page-title">Advisor Review Queue</h1>
          <p className="page-subtitle">
            Review and approve insights before they are delivered to customers.
          </p>
        </div>
      </div>
      {selectedCaseId ? (
        <CaseDetail caseId={selectedCaseId} onBack={() => setSelectedCaseId(null)} />
      ) : (
        <ReviewQueue onSelectCase={setSelectedCaseId} />
      )}
    </div>
  )
}
