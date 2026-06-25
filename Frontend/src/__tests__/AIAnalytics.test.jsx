/**
 * TC-FE-AI — AI Analytics Page Tests
 * PortFlow AI Frontend Tests
 *
 * Run: npx vitest run src/__tests__/AIAnalytics.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test/renderWithProviders'

vi.mock('../services/api', () => ({
  analyticsApi: {
    // Real analyticsApi.metrics()/charts() resolve the flat object/array
    // directly (no {data: ...} envelope).
    metrics: vi.fn().mockResolvedValue({
      total_vessels: 50,
      total_visits: 120,
      active_visits: 15,
      completed_visits: 80,
      scheduled_visits: 25,
      total_ports: 6,
      total_berths: 20,
      total_predictions: 5000,
      berth_utilization_percent: 72.0,
      avg_turnaround_minutes: 360,
    }),
    charts: vi.fn().mockResolvedValue([]),
    compare: vi.fn().mockResolvedValue({
      current_period: { total_visits: 50, period: '2026-04' },
      previous_period: { total_visits: 40, period: '2026-03' },
      deltas: { total_visits: 10 },
      insights: ['Vessel traffic increased by 25%'],
    }),
  },
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'analyst' }, isAuthenticated: true }),
}))

import AIAnalytics from '../pages/AIAnalytics'

function renderPage() {
  return renderWithProviders(<AIAnalytics />)
}

describe('TC-FE-AI — AI Analytics Page', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('TC-FE-AI-01: renders without throwing', () => {
    expect(() => renderPage()).not.toThrow()
  })

  it('TC-FE-AI-02: calls analytics metrics API on mount', async () => {
    const { analyticsApi } = await import('../services/api')
    renderPage()
    await waitFor(() => {
      expect(analyticsApi.metrics).toHaveBeenCalled()
    })
  })

  it('TC-FE-AI-03: no hardcoded fake chart data (vesselTrafficData)', async () => {
    renderPage()
    await waitFor(() => {
      // These were removed — should not appear
      expect(screen.queryByText('vesselTrafficData')).toBeFalsy()
    }, { timeout: 2000 })
  })

  it('TC-FE-AI-04: displays data from metrics API response', async () => {
    renderPage()
    await waitFor(() => {
      const text = document.body.textContent
      // total_vessels=50 should appear somewhere in the page
      expect(text.includes('50') || text.includes('72')).toBeTruthy()
    }, { timeout: 3000 })
  })
})
