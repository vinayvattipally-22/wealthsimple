import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import SavingsSummary from '../components/SavingsSummary'

describe('SavingsSummary', () => {
  it('renders total savings formatted', () => {
    render(<SavingsSummary summary={{ total_identified_savings: 4820.5 }} />)
    expect(screen.getByText(/4,820\.50/)).toBeInTheDocument()
  })

  it('shows act now count when > 0', () => {
    render(<SavingsSummary summary={{ total_identified_savings: 1000, act_now_count: 2 }} />)
    expect(screen.getByText(/2 act now/)).toBeInTheDocument()
  })

  it('shows this year count when > 0', () => {
    render(<SavingsSummary summary={{ total_identified_savings: 1000, this_year_count: 3 }} />)
    expect(screen.getByText(/3 this year/)).toBeInTheDocument()
  })

  it('shows long term count when > 0', () => {
    render(<SavingsSummary summary={{ total_identified_savings: 1000, long_term_count: 1 }} />)
    expect(screen.getByText(/1 long term/)).toBeInTheDocument()
  })

  it('returns null when summary is null', () => {
    const { container } = render(<SavingsSummary summary={null} />)
    expect(container.innerHTML).toBe('')
  })

  it('handles zero savings', () => {
    render(<SavingsSummary summary={{ total_identified_savings: 0 }} />)
    expect(screen.getByText(/0\.00/)).toBeInTheDocument()
  })
})
