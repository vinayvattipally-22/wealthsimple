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

export async function getAdvisorQueue() {
  const res = await fetch(`${BASE}/advisor/queue`, { headers: authHeaders() })
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

export async function sendChatMessage({ question, profileId, pageContext, history }) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      question,
      profile_id: profileId || null,
      page_context: pageContext || '',
      history: history || [],
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.body
}
