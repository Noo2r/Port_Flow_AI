/**
 * TC-FE-RBAC — Role-Based Access Control Tests
 * PortFlow AI Frontend Tests
 *
 * Verifies:
 *   1. Sidebar hides /analytics and /evaluation links for operational roles.
 *   2. Sidebar shows /analytics and /evaluation links for technical roles.
 *   3. CongestionForecast hides the "Model Evaluation" tab for operational roles.
 *   4. CongestionForecast shows the "Model Evaluation" tab for technical roles.
 *
 * Run: npx vitest run src/__tests__/Rbac.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../test/renderWithProviders'

// ── API mocks needed by Sidebar (none directly) and CongestionForecast ────────

vi.mock('../services/api', () => ({
  congestionApi: {
    portOverview: vi.fn().mockResolvedValue({ ports: [], count: 0 }),
    evaluation: vi.fn().mockResolvedValue({
      models: {
        congestion: { name: 'LightGBM', R2: 0.94, MAE: 0.04, grade: 'Excellent' },
        queue:      { name: 'CatBoost', R2: 0.52, MAE: 1.7,  grade: 'Good' },
      },
    }),
    modelInfo: vi.fn().mockResolvedValue({
      congestion_model_name: 'LightGBM', queue_model_name: 'CatBoost', features: 43,
      metrics: {
        congestion: { MAE: 0.04, RMSE: 0.05, R2: 0.94 },
        queue:      { MAE: 1.7,  RMSE: 2.2,  R2: 0.52 },
      },
      feature_importance: { congestion: [], queue: [] },
    }),
    predict: vi.fn().mockResolvedValue({
      congestion_level: 0.4, congestion_pct: 40, congestion_label: 'Medium',
      congestion_color: '#eab308', queue_length: 2, risk_score: 0.3,
      risk_pct: 30, confidence: 0.85, top_factors: [],
      congestion_model: 'LightGBM', queue_model: 'CatBoost',
    }),
  },
  analyticsApi: {
    metrics: vi.fn().mockResolvedValue({}),
    charts:  vi.fn().mockResolvedValue([]),
  },
  berthsApi:  { list: vi.fn().mockResolvedValue([]) },
  visitsApi:  { list: vi.fn().mockResolvedValue([]) },
}))

// AuthContext mock — we override per describe block
const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

import Sidebar           from '../components/Sidebar'
import CongestionForecast from '../pages/CongestionForecast'

// ── Sidebar tests ─────────────────────────────────────────────────────────────

describe('TC-FE-RBAC-SIDEBAR — Sidebar role-gated links', () => {
  beforeEach(() => vi.clearAllMocks())

  it('TC-FE-RBAC-01: hides Analytics and Model Evaluation links for operations role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'operations', full_name: 'Operator' }, logout: vi.fn() })
    renderWithProviders(<Sidebar />)

    // Analytics nav item should not be present
    const links = screen.queryAllByRole('link')
    const hrefs = links.map(l => l.getAttribute('href'))
    expect(hrefs).not.toContain('/analytics')
    expect(hrefs).not.toContain('/evaluation')
  })

  it('TC-FE-RBAC-02: hides Analytics and Model Evaluation links for vessel_agent role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'vessel_agent', full_name: 'Agent' }, logout: vi.fn() })
    renderWithProviders(<Sidebar />)

    const hrefs = screen.queryAllByRole('link').map(l => l.getAttribute('href'))
    expect(hrefs).not.toContain('/analytics')
    expect(hrefs).not.toContain('/evaluation')
  })

  it('TC-FE-RBAC-03: shows Analytics and Model Evaluation links for port_manager role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'port_manager', full_name: 'Manager' }, logout: vi.fn() })
    renderWithProviders(<Sidebar />)

    const hrefs = screen.queryAllByRole('link').map(l => l.getAttribute('href'))
    expect(hrefs).toContain('/analytics')
    expect(hrefs).toContain('/evaluation')
  })

  it('TC-FE-RBAC-04: shows Analytics and Model Evaluation links for analyst role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'analyst', full_name: 'Analyst' }, logout: vi.fn() })
    renderWithProviders(<Sidebar />)

    const hrefs = screen.queryAllByRole('link').map(l => l.getAttribute('href'))
    expect(hrefs).toContain('/analytics')
    expect(hrefs).toContain('/evaluation')
  })

  it('TC-FE-RBAC-05: shows Admin link for admin role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'admin', full_name: 'Admin' }, logout: vi.fn() })
    renderWithProviders(<Sidebar />)

    const hrefs = screen.queryAllByRole('link').map(l => l.getAttribute('href'))
    expect(hrefs).toContain('/admin')
    expect(hrefs).toContain('/analytics')
    expect(hrefs).toContain('/evaluation')
  })

  it('TC-FE-RBAC-06: hides Admin link for non-admin roles', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'operations', full_name: 'Op' }, logout: vi.fn() })
    renderWithProviders(<Sidebar />)

    const hrefs = screen.queryAllByRole('link').map(l => l.getAttribute('href'))
    expect(hrefs).not.toContain('/admin')
  })
})

// ── CongestionForecast tab tests ───────────────────────────────────────────────

describe('TC-FE-RBAC-CONGESTION — Model Evaluation tab visibility', () => {
  beforeEach(() => vi.clearAllMocks())

  it('TC-FE-RBAC-07: hides Model Evaluation tab for operations role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'operations' }, isAuthenticated: true })
    renderWithProviders(<CongestionForecast />)

    expect(screen.queryByText('Model Evaluation')).toBeNull()
    // Live Forecast and Port Overview tabs are always visible
    expect(screen.getByText('Live Forecast')).toBeTruthy()
    expect(screen.getByText('Port Overview')).toBeTruthy()
  })

  it('TC-FE-RBAC-08: shows Model Evaluation tab for port_manager role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'port_manager' }, isAuthenticated: true })
    renderWithProviders(<CongestionForecast />)

    // getAllByText: tab button + possible panel heading both acceptable
    expect(screen.getAllByText('Model Evaluation').length).toBeGreaterThan(0)
  })

  it('TC-FE-RBAC-09: shows Model Evaluation tab for analyst role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'analyst' }, isAuthenticated: true })
    renderWithProviders(<CongestionForecast />)

    expect(screen.getAllByText('Model Evaluation').length).toBeGreaterThan(0)
  })

  it('TC-FE-RBAC-10: shows Model Evaluation tab for admin role', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'admin' }, isAuthenticated: true })
    renderWithProviders(<CongestionForecast />)

    expect(screen.getAllByText('Model Evaluation').length).toBeGreaterThan(0)
  })
})
