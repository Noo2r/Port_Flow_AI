/**
 * TC-FE-CARGO — Cargo & Workforce Page Tests
 * PortFlow AI Frontend Tests
 *
 * Run: npx vitest run src/__tests__/CargoWorkforce.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test/renderWithProviders'

// vi.mock() factories are hoisted above the rest of the module, so a plain
// top-level `const` referenced inside one throws "Cannot access before
// initialization". vi.hoisted() runs before that hoisting, making it safe.
const { mockWorkOrders } = vi.hoisted(() => ({
  mockWorkOrders: Array.from({ length: 15 }, (_, i) => ({
    id: i + 1,
    title: `Work Order ${i + 1}`,
    order_type: 'pilotage',
    status: 'pending',
    priority: 'normal',
    vessel_id: 1,
    visit_id: 1,
    created_at: '2026-01-01T00:00:00Z',
  })),
}))

// Real api.js calls resolve the flat array/object directly (no {data: ...}
// envelope) — see services/api.js's request() helper.
vi.mock('../services/api', () => ({
  workOrdersApi: {
    list: vi.fn().mockResolvedValue(mockWorkOrders),
    create: vi.fn().mockResolvedValue({ id: 99, title: 'New WO', order_type: 'mooring', status: 'pending' }),
  },
  vesselsApi: {
    list: vi.fn().mockResolvedValue([{ id: 1, name: 'MV Alpha', vessel_type: 'container' }]),
  },
  visitsApi: {
    list: vi.fn().mockResolvedValue([{ id: 1, vessel_id: 1, status: 'scheduled' }]),
  },
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'port_manager' }, isAuthenticated: true }),
}))

import CargoWorkforce from '../pages/CargoWorkforce'

function renderPage() {
  return renderWithProviders(<CargoWorkforce />)
}

describe('TC-FE-CARGO — Cargo & Workforce Page', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('TC-FE-CARGO-01: renders work orders from API', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Work Order 1')).toBeTruthy()
    }, { timeout: 3000 })
  })

  it('TC-FE-CARGO-02: "New Work Order" button opens modal', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Work Order 1'))

    const newBtn = screen.getByRole('button', { name: /new work order/i })
    expect(newBtn).toBeTruthy()
    fireEvent.click(newBtn)

    await waitFor(() => {
      // Modal should appear with form fields
      const titleInput = document.querySelector('input[name="title"]') ||
                         screen.queryByPlaceholderText(/title/i)
      expect(titleInput).toBeTruthy()
    })
  })

  it('TC-FE-CARGO-03: work orders API is called on mount', async () => {
    const { workOrdersApi } = await import('../services/api')
    renderPage()
    await waitFor(() => {
      expect(workOrdersApi.list).toHaveBeenCalled()
    })
  })

  it('TC-FE-CARGO-04: page renders first 10 items (pagination)', async () => {
    renderPage()
    await waitFor(() => {
      // With 15 items and PAGE_SIZE=10, only first 10 should be visible
      expect(screen.getByText('Work Order 1')).toBeTruthy()
      expect(screen.queryByText('Work Order 15')).toBeFalsy()
    }, { timeout: 3000 })
  })

  it('TC-FE-CARGO-05: page renders without throwing', () => {
    expect(() => renderPage()).not.toThrow()
  })
})
