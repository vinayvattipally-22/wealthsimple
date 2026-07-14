import { Link } from 'react-router-dom'
import { FileText, CandlestickChart, Shield } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import '../styles/dashboard.css'

const USER_SECTIONS = [
  {
    to: '/tax/documents',
    icon: FileText,
    title: 'Tax Analyzer',
    description: 'Upload documents, analyze taxes, get AI-powered insights and action items.',
    color: 'var(--ws-dark)',
    bgColor: 'var(--ws-blue-light)',
  },
  {
    to: '/stocks',
    icon: CandlestickChart,
    title: 'Stock Research',
    description: 'Research stocks, view market news, and get AI-driven price insights.',
    color: 'var(--ws-green)',
    bgColor: 'var(--ws-green-light)',
  },
]

const ADVISOR_SECTIONS = [
  {
    to: '/tax/advisor',
    icon: Shield,
    title: 'Tax Review Queue',
    description: 'Review AI-generated tax insights, add feedback, and approve or reject before delivery to clients.',
    color: 'var(--ws-dark)',
    bgColor: 'var(--ws-blue-light)',
  },
  {
    to: '/stocks/review',
    icon: CandlestickChart,
    title: 'Stock Insights Review',
    description: 'Verify AI-generated stock insights are correct before they reach users.',
    color: 'var(--ws-green)',
    bgColor: 'var(--ws-green-light)',
  },
]

export default function Home() {
  const { isAdvisor } = useAuth()
  const sections = isAdvisor ? ADVISOR_SECTIONS : USER_SECTIONS

  return (
    <div className="page-container animate-fade-in">
      <div className="home-header">
        <h1 className="page-title">Welcome to TaxFolio</h1>
        <p className="page-subtitle">
          {isAdvisor ? 'Advisor Portal — Review and approve AI-generated insights' : 'Choose a section to get started'}
        </p>
      </div>
      <div className="home-cards">
        {sections.map(({ to, icon: Icon, title, description, color, bgColor }) => (
          <Link key={to} to={to} className="home-card card card-interactive">
            <div className="home-card-icon" style={{ background: bgColor, color }}>
              <Icon size={32} />
            </div>
            <h2 className="home-card-title">{title}</h2>
            <p className="home-card-desc">{description}</p>
            <span className="home-card-cta">Get started &rarr;</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
