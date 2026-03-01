/** Backend API calls */
const BASE = '/api'

function authHeaders(extra = {}) {
  const headers = { ...extra }
  const token = localStorage.getItem('token')
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

export async function uploadDocument(formData) {
  const res = await fetch(`${BASE}/upload`, { method: 'POST', headers: authHeaders(), body: formData })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createProfile(data) {
  const res = await fetch(`${BASE}/profiles`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateProfile(profileId, data) {
  const res = await fetch(`${BASE}/profiles/${profileId}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getAnalysisStatus(profileId) {
  const res = await fetch(`${BASE}/analysis/${profileId}/status`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getAnalysisResults(profileId) {
  const res = await fetch(`${BASE}/analysis/${profileId}/results`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getDashboardData(profileId) {
  const res = await fetch(`${BASE}/analysis/${profileId}/dashboard`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function triggerAnalysis(profileId) {
  const res = await fetch(`${BASE}/analyze/${profileId}`, { method: 'POST', headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getTrends(userId) {
  const res = await fetch(`${BASE}/trends?user_id=${userId}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getAdvisorQueue(status = 'PENDING') {
  const res = await fetch(`${BASE}/advisor/queue?status=${status}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getCase(caseId) {
  const res = await fetch(`${BASE}/advisor/case/${caseId}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function approveCase(caseId, body = {}) {
  const res = await fetch(`${BASE}/advisor/case/${caseId}/approve`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function rejectCase(caseId, body = {}) {
  const res = await fetch(`${BASE}/advisor/case/${caseId}/reject`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function escalateCase(caseId, body = {}) {
  const res = await fetch(`${BASE}/advisor/case/${caseId}/escalate`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function commentInsight(caseId, insightId, comment) {
  const res = await fetch(`${BASE}/advisor/case/${caseId}/comment`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ insight_id: insightId, comment }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function approveInsight(caseId, insightId, comment = '') {
  const res = await fetch(`${BASE}/advisor/case/${caseId}/insight/${insightId}/approve`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ comment }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function rejectInsight(caseId, insightId, comment = '') {
  const res = await fetch(`${BASE}/advisor/case/${caseId}/insight/${insightId}/reject`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ comment }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function downloadReport(profileId) {
  const res = await fetch(`${BASE}/reports/${profileId}/pdf`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.blob()
}

export async function getUserDashboard(profileId) {
  const url = profileId
    ? `${BASE}/user/dashboard?profile_id=${profileId}`
    : `${BASE}/user/dashboard`
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getUserDocuments() {
  const res = await fetch(`${BASE}/user/documents`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getActionItems(profileId) {
  const url = profileId
    ? `${BASE}/action-items?profile_id=${profileId}`
    : `${BASE}/action-items`
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateActionItem(itemId, data) {
  const res = await fetch(`${BASE}/action-items/${itemId}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function runScenario(profileId, scenarioType, value) {
  const res = await fetch(`${BASE}/simulator/run`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      profile_id: profileId,
      scenario_type: scenarioType,
      value,
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getAdvisorData(profileId) {
  const url = profileId
    ? `${BASE}/user/advisor?profile_id=${profileId}`
    : `${BASE}/user/advisor`
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function searchStocks(query) {
  const res = await fetch(`${BASE}/stocks/search?q=${encodeURIComponent(query)}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getResearchHistory(limit = 20) {
  const res = await fetch(`${BASE}/stocks/history?limit=${limit}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getResearchDetail(researchId) {
  const res = await fetch(`${BASE}/stocks/research/${researchId}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function runBacktest(ticker, signal, lookbackDays = 90) {
  const res = await fetch(`${BASE}/stocks/backtest`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ ticker, signal, lookback_days: lookbackDays }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function getAuthToken() {
  return localStorage.getItem('token')
}

export async function getStockNews(ticker, limit = 30, offset = 0) {
  const res = await fetch(
    `${BASE}/stocks/${encodeURIComponent(ticker)}/news?limit=${limit}&offset=${offset}`,
    { headers: authHeaders() }
  )
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function refreshStockNews(ticker) {
  const res = await fetch(
    `${BASE}/stocks/${encodeURIComponent(ticker)}/news/refresh`,
    { method: 'POST', headers: authHeaders() }
  )
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getStockInsights(ticker) {
  const res = await fetch(
    `${BASE}/stocks/${encodeURIComponent(ticker)}/insights`,
    { headers: authHeaders() }
  )
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function generateStockInsights(ticker) {
  const res = await fetch(
    `${BASE}/stocks/${encodeURIComponent(ticker)}/insights/generate`,
    { method: 'POST', headers: authHeaders() }
  )
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getStockAdvisorQueue(status = 'PENDING') {
  const res = await fetch(`${BASE}/advisor/stock-queue?status=${status}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function approveStockInsight(insightId, comment = '') {
  const res = await fetch(`${BASE}/advisor/stock-insight/${insightId}/approve`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ comment }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function rejectStockInsight(insightId, comment = '') {
  const res = await fetch(`${BASE}/advisor/stock-insight/${insightId}/reject`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ comment }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function sendChatMessage({ question, profileId, pageContext, pageDataSummary, userId, history }) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      question,
      profile_id: profileId || null,
      page_context: pageContext || '',
      page_data_summary: pageDataSummary || '',
      user_id: userId || null,
      history: history || [],
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.body
}
