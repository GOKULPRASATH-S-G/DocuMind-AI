const API_BASE = '/api/v1';

function getAuthHeaders(extraHeaders = {}) {
  const token = localStorage.getItem('token');
  const headers = { ...extraHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

function parseApiError(data, fallback = 'Request failed') {
  if (!data) return fallback;
  const detail = data.detail || data.message || data.error;
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(d => (typeof d === 'string' ? d : (d.msg || JSON.stringify(d)))).join('; ');
  }
  if (typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return String(detail);
}

export async function registerUser(email, password, role = 'USER') {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err, 'Registration failed'));
  }
  return res.json();
}

export async function loginUser(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err, 'Login failed'));
  }
  const data = await res.json();
  if (data.access_token) {
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
  }
  return data;
}

export async function getMe() {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch user profile');
  return res.json();
}

export function logoutUser() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function processDocument(documentId) {
  const res = await fetch(`${API_BASE}/documents/${documentId}/process`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(parseApiError(errData, 'Document page processing failed.'));
  }
  return res.json();
}

export async function extractStructuredData(documentId) {
  const res = await fetch(`${API_BASE}/documents/${documentId}/extract`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Structured extraction failed');
  }
  return res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/documents`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function fetchDocumentDetail(documentId) {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch document detail');
  return res.json();
}

export async function deleteDocument(documentId) {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete document');
  }
  return res.json();
}

// Phase 5 HITL Review API Helpers
export async function fetchReviews(status = 'NEEDS_REVIEW', page = 1, pageSize = 20, sortBy = 'date_desc') {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    sort_by: sortBy,
  });
  if (status) params.append('status', status);

  const res = await fetch(`${API_BASE}/reviews?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch review queue');
  return res.json();
}

export async function fetchReviewDetail(reviewId) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch review details');
  return res.json();
}

export async function updateReviewField(reviewId, field, value) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/fields`, {
    method: 'PATCH',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ field, value }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update field value');
  }
  return res.json();
}

export async function approveReview(reviewId) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/approve`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to approve document');
  }
  return res.json();
}

export async function rejectReview(reviewId, reason) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/reject`, {
    method: 'POST',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to reject document');
  }
  return res.json();
}

export async function indexDocument(documentId) {
  const res = await fetch(`${API_BASE}/documents/${documentId}/index`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Indexing failed');
  }
  return res.json();
}

export async function searchVectorStore(query, topK = 5, documentId = null) {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      query: query,
      top_k: topK,
      document_id: documentId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Semantic search failed');
  }
  return res.json();
}

export async function askQA(query, topK = 5, documentId = null) {
  const res = await fetch(`${API_BASE}/qa`, {
    method: 'POST',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      query: query,
      top_k: topK,
      document_id: documentId || null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Grounded QA synthesis failed');
  }
  return res.json();
}

export function getDocumentFileUrl(documentId) {
  const token = localStorage.getItem('token');
  return token
    ? `${API_BASE}/documents/${documentId}/file?token=${encodeURIComponent(token)}`
    : `${API_BASE}/documents/${documentId}/file`;
}

export function getVisualArtifactImageUrl(documentId, imageId) {
  return `${API_BASE}/documents/${documentId}/images/${imageId}`;
}

// Phase 9 & 10 Evaluation & Metrics API Helpers
export async function runEvaluation(dataset = 'phase9_questions') {
  const res = await fetch(`${API_BASE}/evaluation/run`, {
    method: 'POST',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ dataset }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Evaluation run failed');
  }
  return res.json();
}

export async function fetchEvaluationRuns() {
  const res = await fetch(`${API_BASE}/evaluation/runs`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch evaluation runs');
  return res.json();
}

export async function fetchEvaluationRunDetail(runId) {
  const res = await fetch(`${API_BASE}/evaluation/runs/${runId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch evaluation run details');
  return res.json();
}

export async function fetchProductionMetrics() {
  const res = await fetch(`${API_BASE}/metrics`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch production metrics');
  return res.json();
}

export async function fetchSystemHealth() {
  const res = await fetch(`${API_BASE}/health/ready`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    return data.detail || { status: 'not_ready', database: 'failed', vector_store: 'failed', storage: 'failed' };
  }
  return res.json();
}
