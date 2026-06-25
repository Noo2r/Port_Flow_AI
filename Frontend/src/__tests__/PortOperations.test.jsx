/**
 * TC-FE-PORTOPS — Port Operations Page Tests
 * PortFlow AI Frontend Tests
 *
 * Run: npx vitest run src/__tests__/PortOperations.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test/renderWithProviders'

// Real api.js calls resolve the flat object directly (no {data: ...} envelope).
vi.mock('../services/api', () => ({
  portOpsApi: {
    portKpis: vi.fn().mockResolvedValue({
      total_allocations: 42,
      completed_visits: 40,
      active_vessels: 2,
      avg_waiting_time_minutes: 35.5,
      avg_berth_utilization: 0.45,
      conflict_rate: 0.0,
      conflict_count: 0,
      congestion_rate: 0.0,
      congestion_count: 0,
      kpi_mode: 'live',
    }),
    berthStatus: vi.fn().mockResolvedValue({
      data_mode: 'live',
      berths: [
        { berth_id: 'PORT_A_B00', berth_name: 'Berth 1', status: 'occupied', berth_type: 'container' },
        { berth_id: 'PORT_A_B01', berth_name: 'Berth 2', status: 'available', berth_type: 'bulk' },
      ],
    }),
    allocations: vi.fn().mockResolvedValue({
      allocations: [
        { vessel: 'MV Alpha', berth: 'PORT_A_B00', status: 'in_port', conflict_flag: false, congestion_flag: false },
      ],
    }),
    health: vi.fn().mockResolvedValue({ status: 'healthy', berths_loaded: 96 }),
  },
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'port_manager' }, isAuthenticated: true }),
}))

import PortOperations from '../pages/PortOperations'

function renderPage() {
  return renderWithProviders(<PortOperations />)
}

describe('TC-FE-PORTOPS — Port Operations Page', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('TC-FE-PORTOPS-01: renders without throwing', () => {
    expect(() => renderPage()).not.toThrow()
  })

  it('TC-FE-PORTOPS-02: calls all four port-ops APIs on mount', async () => {
    const { portOpsApi } = await import('../services/api')
    renderPage()
    await waitFor(() => {
      expect(portOpsApi.portKpis).toHaveBeenCalled()
      expect(portOpsApi.berthStatus).toHaveBeenCalled()
      expect(portOpsApi.allocations).toHaveBeenCalled()
      expect(portOpsApi.health).toHaveBeenCalled()
    })
  })

  it('TC-FE-PORTOPS-03: displays active vessel count from live KPI data', async () => {
    renderPage()
    await waitFor(() => {
      expect(document.body.textContent).toContain('Active Vessels')
      // active_vessels: 2 from the mock
      expect(document.body.textContent).toMatch(/\b2\b/)
    }, { timeout: 3000 })
  })

  it('TC-FE-PORTOPS-04: berth status list reflects API data, not hardcoded berths', async () => {
    renderPage()
    await waitFor(() => {
      // Real berth count (2) must drive the "berths" sub-label, not a fake number
      expect(document.body.textContent).toMatch(/2 berths/i)
    }, { timeout: 3000 })
  })

  it('TC-FE-PORTOPS-05: two mounted instances share one cached request, not two', async () => {
    // This is the core "shared data layer" guarantee from the Task 1 React
    // Query refactor: two components reading the same query key collapse
    // into a single network call instead of each firing its own.
    const { portOpsApi } = await import('../services/api')
    renderWithProviders(
      <>
        <PortOperations />
        <PortOperations />
      </>
    )
    await waitFor(() => expect(portOpsApi.portKpis).toHaveBeenCalledTimes(1))
  })
})
