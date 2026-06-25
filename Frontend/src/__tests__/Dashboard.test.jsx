/**
 * TC-FE-DASH — Dashboard Page Tests
 * PortFlow AI Frontend Tests
 *
 * Run: npx vitest run src/__tests__/Dashboard.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test/renderWithProviders'

vi.mock('../services/api', () => ({
  analyticsApi: {
    // Real analyticsApi.metrics() resolves the flat object directly (no
    // {data: ...} envelope) — Dashboard.jsx reads metrics?.total_vessels etc.
    metrics: vi.fn().mockResolvedValue({
      total_vessels: 42,
      total_visits: 88,
      active_visits: 12,
      completed_visits: 56,
      scheduled_visits: 20,
      total_ports: 5,
      total_berths: 18,
      total_predictions: 1500,
      berth_utilization_percent: 67.5,
      avg_turnaround_minutes: 240,
    }),
    charts: vi.fn().mockResolvedValue([]),
  },
  berthsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
  visitsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'admin', full_name: 'Admin User' }, isAuthenticated: true }),
}))

import Dashboard from '../pages/Dashboard'

function renderDashboard() {
  return renderWithProviders(<Dashboard />)
}

describe('TC-FE-DASH — Dashboard Page', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('TC-FE-DASH-01: renders without crashing', () => {
    expect(() => renderDashboard()).not.toThrow()
  })

  it('TC-FE-DASH-02: calls analytics metrics API on mount', async () => {
    const { analyticsApi } = await import('../services/api')
    renderDashboard()
    await waitFor(() => {
      expect(analyticsApi.metrics).toHaveBeenCalled()
    })
  })

  it('TC-FE-DASH-03: displays vessel count from API response', async () => {
    renderDashboard()
    await waitFor(() => {
      // The number 42 should appear somewhere in the dashboard stats
      expect(document.body.textContent.includes('42')).toBe(true)
    }, { timeout: 3000 })
  })

  it('TC-FE-DASH-04: shows no hardcoded fake vessel names', async () => {
    renderDashboard()
    await waitFor(() => {
      // These are common mock data names — none should appear
      expect(screen.queryByText('MSC Colombo')).toBeFalsy()
      expect(screen.queryByText('Ever Given')).toBeFalsy()
      expect(screen.queryByText('Emma Maersk')).toBeFalsy()
    }, { timeout: 2000 })
  })
})
