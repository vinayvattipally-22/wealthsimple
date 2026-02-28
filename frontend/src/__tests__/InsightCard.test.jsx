import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import InsightCard from '../components/InsightCard'

describe('InsightCard', () => {
  const baseInsight = {
    headline: 'Maximize RRSP contribution',
    detail: 'Contributing $12,000 to RRSP would reduce taxable income.',
    estimated_value: 3120.0,
    category: 'THIS_YEAR',
    action_required: 'Contribute before March 1 deadline',
    product_link: 'wealthsimple://rrsp',
  }

  it('renders headline', () => {
    render(<InsightCard insight={baseInsight} />)
    expect(screen.getByText(/Maximize RRSP contribution/)).toBeInTheDocument()
  })

  it('renders detail text after expanding', () => {
    render(<InsightCard insight={baseInsight} />)
    // Detail is hidden by default; click to expand
    fireEvent.click(screen.getByText(/Maximize RRSP contribution/))
    expect(screen.getByText(/Contributing \$12,000/)).toBeInTheDocument()
  })

  it('renders estimated value formatted', () => {
    render(<InsightCard insight={baseInsight} />)
    expect(screen.getByText(/3,120\.00/)).toBeInTheDocument()
  })

  it('renders action required after expanding', () => {
    render(<InsightCard insight={baseInsight} />)
    // Action required is hidden by default; click to expand
    fireEvent.click(screen.getByText(/Maximize RRSP contribution/))
    expect(screen.getByText('Contribute before March 1 deadline')).toBeInTheDocument()
  })

  it('does not render product link', () => {
    render(<InsightCard insight={baseInsight} />)
    expect(screen.queryByText(/Open in Wealthsimple/)).not.toBeInTheDocument()
  })

  it('returns null for null insight', () => {
    const { container } = render(<InsightCard insight={null} />)
    expect(container.innerHTML).toBe('')
  })

  it('applies red border for ACT_NOW category', () => {
    const insight = { ...baseInsight, category: 'ACT_NOW' }
    const { container } = render(<InsightCard insight={insight} />)
    const card = container.firstChild
    expect(card.style.borderLeft).toContain('rgb(204, 0, 0)')
  })

  it('applies green border for LONG_TERM category', () => {
    const insight = { ...baseInsight, category: 'LONG_TERM' }
    const { container } = render(<InsightCard insight={insight} />)
    const card = container.firstChild
    expect(card.style.borderLeft).toContain('rgb(34, 139, 34)')
  })
})
