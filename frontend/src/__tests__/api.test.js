import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Import after mocking
import {
  uploadDocument,
  createProfile,
  getAnalysisStatus,
  getAnalysisResults,
  triggerAnalysis,
  getAdvisorQueue,
  getCase,
  approveCase,
  rejectCase,
} from '../services/api'

describe('API service', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('uploadDocument sends POST with FormData', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ '14': 55000 }) })
    const formData = new FormData()
    const result = await uploadDocument(formData)
    expect(mockFetch).toHaveBeenCalledWith('/api/upload', expect.objectContaining({ method: 'POST', body: formData }))
    expect(result['14']).toBe(55000)
  })

  it('createProfile sends JSON body', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ profile_id: 1 }) })
    const result = await createProfile({ tax_year: 2024 })
    expect(mockFetch).toHaveBeenCalledWith('/api/profiles', expect.objectContaining({ method: 'POST' }))
    expect(result.profile_id).toBe(1)
  })

  it('getAnalysisStatus fetches GET', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ review_status: 'PENDING' }) })
    const result = await getAnalysisStatus(1)
    expect(mockFetch).toHaveBeenCalledWith('/api/analysis/1/status', expect.objectContaining({ headers: {} }))
    expect(result.review_status).toBe('PENDING')
  })

  it('getAnalysisResults fetches results', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ insights: [] }) })
    const result = await getAnalysisResults(1)
    expect(result.insights).toEqual([])
  })

  it('triggerAnalysis sends POST', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ case_id: 1, insights_count: 3 }) })
    const result = await triggerAnalysis(1)
    expect(mockFetch).toHaveBeenCalledWith('/api/analyze/1', expect.objectContaining({ method: 'POST' }))
    expect(result.insights_count).toBe(3)
  })

  it('getAdvisorQueue fetches queue', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ queue: [{ case_id: 1 }] }) })
    const result = await getAdvisorQueue()
    expect(result.queue).toHaveLength(1)
  })

  it('approveCase sends POST with body', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ status: 'APPROVED' }) })
    const result = await approveCase(1, {})
    expect(result.status).toBe('APPROVED')
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, text: () => Promise.resolve('Not found') })
    await expect(getAnalysisStatus(999)).rejects.toThrow('Not found')
  })
})
