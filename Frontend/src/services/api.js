/**
 * PortFlow AI — API client
 * Thin wrapper around fetch that handles:
 *  - Base URL from env
 *  - Auth Bearer token (auto-attached from localStorage)
 *  - Token refresh on 401
 *  - Consistent error shape
 */

// In dev, Vite proxy forwards /api → http://localhost:8000
// In production, set VITE_API_BASE_URL to your backend URL
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

function getTokens() {
  return {
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
  }
}

function saveTokens({ access_token, refresh_token }) {
  if (access_token)  localStorage.setItem('access_token', access_token)
  if (refresh_token) localStorage.setItem('refresh_token', refresh_token)
}

function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

async function refreshAccessToken() {
  const { refresh } = getTokens()
  if (!refresh) throw new Error('No refresh token')
  const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refresh }),
  })
  if (!res.ok) {
    clearTokens()
    window.location.href = '/login'
    throw new Error('Session expired')
  }
  const data = await res.json()
  saveTokens(data)
  return data.access_token
}

async function request(path, options = {}, retry = true) {
  const { access } = getTokens()
  const headers = {
    'Content-Type': 'application/json',
    ...(access ? { Authorization: `Bearer ${access}` } : {}),
    ...options.headers,
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (res.status === 401 && retry) {
    try {
      const newToken = await refreshAccessToken()
      return request(path, {
        ...options,
        headers: { ...options.headers, Authorization: `Bearer ${newToken}` },
      }, false)
    } catch {
      clearTokens()
      window.location.href = '/login'
      throw new Error('Unauthorized')
    }
  }

  if (res.status === 204) return null

  const data = await res.json().catch(() => null)

  if (!res.ok) {
    const message = data?.detail || data?.error || `Request failed: ${res.status}`
    throw new Error(message)
  }

  return data
}

// ── Convenience methods ───────────────────────────────────────────────────────
const api = {
  get:    (path, opts = {}) => request(path, { method: 'GET',    ...opts }),
  post:   (path, body, opts = {}) => request(path, { method: 'POST',   body: JSON.stringify(body), ...opts }),
  patch:  (path, body, opts = {}) => request(path, { method: 'PATCH',  body: JSON.stringify(body), ...opts }),
  delete: (path, opts = {}) => request(path, { method: 'DELETE', ...opts }),
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) =>
    request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  loginForm: (email, password) => {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    return request('/api/v1/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    })
  },

  register:        (data) => api.post('/api/v1/auth/register', data),
  adminCreateUser: (data) => api.post('/api/v1/auth/users', data),
  logout:          () => api.post('/api/v1/auth/logout', {}),
  me:              () => api.get('/api/v1/auth/me'),
  forgotPassword:  (email) => api.post('/api/v1/auth/forgot-password', { email }),
  resetPassword:   (token, password) => api.post('/api/v1/auth/reset-password', { token, new_password: password }),
}

// ── Vessels ───────────────────────────────────────────────────────────────────
export const vesselsApi = {
  list:   (skip = 0, limit = 100) => api.get(`/api/v1/vessels/?skip=${skip}&limit=${limit}`),
  get:    (id) => api.get(`/api/v1/vessels/${id}`),
  create: (data) => api.post('/api/v1/vessels/', data),
  update: (id, data) => api.patch(`/api/v1/vessels/${id}`, data),
  delete: (id) => api.delete(`/api/v1/vessels/${id}`),
}

// ── Ports ─────────────────────────────────────────────────────────────────────
export const portsApi = {
  list:   (skip = 0, limit = 4000) => api.get(`/api/v1/ports/?skip=${skip}&limit=${limit}`),
  get:    (id) => api.get(`/api/v1/ports/${id}`),
  create: (data) => api.post('/api/v1/ports/', data),
  update: (id, data) => api.patch(`/api/v1/ports/${id}`, data),
  delete: (id) => api.delete(`/api/v1/ports/${id}`),
}

// ── Berths ────────────────────────────────────────────────────────────────────
export const berthsApi = {
  list:   (skip = 0, limit = 100) => api.get(`/api/v1/berths/?skip=${skip}&limit=${limit}`),
  get:    (id) => api.get(`/api/v1/berths/${id}`),
  create: (data) => api.post('/api/v1/berths/', data),
  update: (id, data) => api.patch(`/api/v1/berths/${id}`, data),
  delete: (id) => api.delete(`/api/v1/berths/${id}`),
}

// ── Visits ────────────────────────────────────────────────────────────────────
export const visitsApi = {
  list:   (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/api/v1/visits/?${q}`)
  },
  get:    (id) => api.get(`/api/v1/visits/${id}`),
  create: (data) => api.post('/api/v1/visits/', data),
  update: (id, data) => api.patch(`/api/v1/visits/${id}`, data),
  delete: (id) => api.delete(`/api/v1/visits/${id}`),
}

// ── Voyages ───────────────────────────────────────────────────────────────────
export const voyagesApi = {
  list:   (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/api/v1/voyages/?${q}`)
  },
  get:    (id) => api.get(`/api/v1/voyages/${id}`),
  create: (data) => api.post('/api/v1/voyages/', data),
  update: (id, data) => api.patch(`/api/v1/voyages/${id}`, data),
  delete: (id) => api.delete(`/api/v1/voyages/${id}`),
}

// ── Work Orders ───────────────────────────────────────────────────────────────
export const workOrdersApi = {
  list:   (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/api/v1/work-orders?${q}`)
  },
  get:    (id) => api.get(`/api/v1/work-orders/${id}`),
  create: (data) => api.post('/api/v1/work-orders', data),
  update: (id, data) => api.patch(`/api/v1/work-orders/${id}`, data),
  delete: (id) => api.delete(`/api/v1/work-orders/${id}`),
}

// ── Predictions ───────────────────────────────────────────────────────────────
export const predictionsApi = {
  list:   (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/api/v1/predictions/?${q}`)
  },
  get:    (id) => api.get(`/api/v1/predictions/${id}`),
  create: (data) => api.post('/api/v1/predictions/', data),
  update: (id, data) => api.patch(`/api/v1/predictions/${id}`, data),
}

// ── ETA Predictions (ML model) ────────────────────────────────────────────────
export const etaApi = {
  predict:         (data) => api.post('/api/v1/ai/predict/eta', data),
  predictWithBerth:(data) => api.post('/api/v1/ai/predict/eta-and-berth', data),
  modelInfo:       () => api.get('/api/v1/ai/model-info'),
  evaluation:      () => api.get('/api/v1/ai/evaluation'),
  setActiveModel:  (model_name) => api.post('/api/v1/ai/set-active-model', { model_name }),
  list:            (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/api/v1/predictions/?prediction_type=eta&${q}`)
  },
  updateActuals: (id, data) => api.patch(`/api/v1/predictions/${id}`, data),
}

// ── Stage 3: Congestion Forecast ──────────────────────────────────────────────
export const congestionApi = {
  predict:      (data) => api.post('/api/v1/congestion/predict', data),
  modelInfo:    ()     => api.get('/api/v1/congestion/model-info'),
  portOverview: ()     => api.get('/api/v1/congestion/port-overview'),
  evaluation:   ()     => api.get('/api/v1/congestion/evaluation'),
}

// ── Port Operations (Stage-2 Berth Optimizer) ─────────────────────────────────
export const portOpsApi = {
  health:      () => api.get('/api/v1/port-ops/health'),
  berthStatus: () => api.get('/api/v1/port-ops/berth-status'),
  portKpis:    () => api.get('/api/v1/port-ops/port-kpis'),
  allocations: () => api.get('/api/v1/port-ops/allocations'),
  clearExpired:(hours = 48) => api.delete(`/api/v1/port-ops/allocations/expired?cutoff_hours=${hours}`),
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsApi = {
  metrics: () => api.get('/api/v1/analytics/metrics'),
  charts:  (days = 14) => api.get(`/api/v1/analytics/charts?days=${days}`),
  compare: (year, month) => {
    const q = new URLSearchParams({ ...(year && { year }), ...(month && { month }) }).toString()
    return api.get(`/api/v1/analytics/metrics/compare?${q}`)
  },
}

// ── Notifications ─────────────────────────────────────────────────────────────
export const notificationsApi = {
  list:       () => api.get('/api/v1/notifications'),
  send:       (data) => api.post('/api/v1/notifications/send', data),
  templates:  () => api.get('/api/v1/notifications/templates'),
}

// ── Operations ────────────────────────────────────────────────────────────────
export const operationsApi = {
  updateAIS:       (visitId, data) => api.post(`/api/v1/ops/visits/${visitId}/ais`, data),
  weatherImpact:   (visitId) => api.get(`/api/v1/ops/visits/${visitId}/weather-impact`),
  berthConflicts:  (berthId) => api.get(`/api/v1/ops/berths/${berthId}/conflicts`),
}

// ── Optimization ──────────────────────────────────────────────────────────────
export const optimizationApi = {
  optimize: (data) => api.post('/api/v1/opt/optimize', data),
}

// ── AI Chatbot ────────────────────────────────────────────────────────────────
export const chatApi = {
  message:     (message, history = []) => api.post('/api/v1/chat/message', { message, history }),
  suggestions: () => api.get('/api/v1/chat/suggestions'),
}

// ── Health ────────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () => api.get('/api/v1/health'),
}

export { saveTokens, clearTokens }
export default api
