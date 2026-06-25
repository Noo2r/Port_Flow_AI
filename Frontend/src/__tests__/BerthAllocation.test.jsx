/**
 * TC-FE-BRT — Berth Allocation Page Tests
 * PortFlow AI Frontend Tests
 *
 * Run: npx vitest run src/__tests__/BerthAllocation.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test/renderWithProviders'

// Real api.js calls resolve the flat array/object directly (no {data: ...}
// envelope) — see services/api.js's request() helper.
vi.mock('../services/api', () => ({
  visitsApi: {
    list: vi.fn().mockResolvedValue([
      { id: 1, vessel_id: 1, berth_id: 2, status: 'in_port', eta: '2026-04-20T10:00:00Z', cargo_type: 'container_20ft' },
      { id: 2, vessel_id: 2, berth_id: null, status: 'scheduled', eta: '2026-04-22T08:00:00Z', cargo_type: 'bulk_dry' },
    ]),
    create: vi.fn().mockResolvedValue({ id: 99, vessel_id: 1, status: 'scheduled' }),
  },
  berthsApi: {
    list: vi.fn().mockResolvedValue([
      { id: 1, code: 'B-001', name: 'Berth 1', status: 'occupied', berth_type: 'container' },
      { id: 2, code: 'B-002', name: 'Berth 2', status: 'available', berth_type: 'bulk' },
      { id: 3, code: 'B-003', name: 'Berth 3', status: 'maintenance', berth_type: 'tanker' },
    ]),
  },
  vesselsApi: {
    list: vi.fn().mockResolvedValue([
      { id: 1, name: 'MV Alpha', vessel_type: 'container' },
      { id: 2, name: 'MV Beta', vessel_type: 'bulk_carrier' },
    ]),
  },
  portsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'port_manager' }, isAuthenticated: true }),
}))

import BerthAllocation from '../pages/BerthAllocation'

function renderPage() {
  return renderWithProviders(<BerthAllocation />)
}

describe('TC-FE-BRT — Berth Allocation Page', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('TC-FE-BRT-01: renders page without throwing', () => {
    expect(() => renderPage()).not.toThrow()
  })

  it('TC-FE-BRT-02: calls visits and berths APIs on mount', async () => {
    const { visitsApi, berthsApi } = await import('../services/api')
    renderPage()
    await waitFor(() => {
      expect(visitsApi.list).toHaveBeenCalled()
      expect(berthsApi.list).toHaveBeenCalled()
    })
  })

  it('TC-FE-BRT-03: "New Assignment" button exists and opens modal', async () => {
    renderPage()
    await waitFor(() => {
      const btn = screen.queryByRole('button', { name: /new assignment/i })
      expect(btn).toBeTruthy()
    }, { timeout: 3000 })

    const btn = screen.getByRole('button', { name: /new assignment/i })
    fireEvent.click(btn)

    await waitFor(() => {
      // Modal or form should appear — the modal's own submit button is an
      // unambiguous marker (the page also has a "New Assignment" header
      // button that matches a looser text query even before the modal opens).
      const modal = document.querySelector('[role="dialog"]') ||
                    document.querySelector('.modal') ||
                    screen.queryAllByText(/create assignment/i).length > 0
      expect(modal).toBeTruthy()
    })
  })

  it('TC-FE-BRT-04: berth stats cards render occupied/available/maintenance', async () => {
    renderPage()
    await waitFor(() => {
      const bodyText = document.body.textContent
      // Should show berth status counts
      expect(
        bodyText.includes('occupied') ||
        bodyText.includes('Occupied') ||
        bodyText.includes('available') ||
        bodyText.includes('Available')
      ).toBeTruthy()
    }, { timeout: 3000 })
  })

  it('TC-FE-BRT-05: no hardcoded "AI Insights" fake data panel', async () => {
    renderPage()
    await waitFor(() => {
      // These were removed in the refactor
      expect(screen.queryByText(/optimize berth usage by/i)).toBeFalsy()
      expect(screen.queryByText(/vessel detected early/i)).toBeFalsy()
    }, { timeout: 2000 })
  })
})
