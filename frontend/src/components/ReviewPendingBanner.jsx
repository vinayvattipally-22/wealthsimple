import { Clock } from 'lucide-react'

export default function ReviewPendingBanner({ message }) {
  return (
    <div className="review-pending-banner">
      <Clock size={18} className="banner-icon" />
      <div>
        <strong>Under Advisor Review</strong>
        <p>{message || 'Your AI-generated insights are being reviewed by a financial advisor. They will appear here once approved.'}</p>
      </div>
    </div>
  )
}
